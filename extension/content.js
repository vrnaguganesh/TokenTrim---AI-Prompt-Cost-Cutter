/**
 * TokenTrim - Content Script for ChatGPT, Gemini, and Claude
 * Injects local NLP compression engine and updates rich-text editors reactively.
 */

const FILLER_PHRASES = [
  /please note that/gi,
  /it is important to remember that/gi,
  /in order to/gi,
  /as a matter of fact/gi,
  /due to the fact that/gi,
  /with reference to/gi,
  /in the event that/gi,
  /at this point in time/gi,
  /for the purpose of/gi,
  /it is worth mentioning that/gi,
  /it should be noted that/gi,
  /would like to point out that/gi,
  /needless to say/gi,
  /first and foremost/gi,
  /in my opinion/gi,
  /to be honest/gi,
  /more or less/gi,
  /so as to/gi,
  /with respect to/gi
];

const CONVERSATIONAL_NOISE = [
  /hey\s+[^,]+,\s*/gi,
  /hello\s+[^,]+,\s*/gi,
  /can you please/gi,
  /could you help me to/gi,
  /i am looking for/gi,
  /i would appreciate it if you could/gi,
  /thank you in advance/gi,
  /thanks!/gi,
  /thanks in advance/gi
];

const STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'but', 'or', 'as', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 
  'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 
  'down', 'in', 'on', 'over', 'under', 'again', 'further', 'then', 'once'
]);

function computeJaccardSimilarity(tokensA, tokensB) {
  const setA = new Set(tokensA.filter(t => t && !t.startsWith('__')));
  const setB = new Set(tokensB.filter(t => t && !t.startsWith('__')));
  
  if (setA.size === 0 || setB.size === 0) return 0;

  let intersection = 0;
  setA.forEach(token => {
    if (setB.has(token)) intersection++;
  });

  const union = setA.size + setB.size - intersection;
  return intersection / union;
}

function sanitizeOptimizedPrompt(text) {
  if (!text) return '';

  let cleaned = text
    .normalize('NFKC')
    .replace(/\r\n/g, '\n')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF\uFE0F\u200D]/gu, ' ')
    .replace(/[#*•>\-|–—|]+/g, ' ')
    .replace(/[\[\]{}()<>]+/g, ' ')
    .replace(/[@#$%^&+=~`/\\]+/g, ' ')
    .replace(/"|“|”/g, ' ')
    .replace(/[!?.,;:]{2,}/g, (m) => m.charAt(0))
    .replace(/\s+([.,!?;:])/g, '$1')
    .replace(/([.,!?;:])\s{2,}/g, '$1 ')
    .replace(/\s{2,}/g, ' ')
    .replace(/\n\s+/g, '\n')
    .replace(/\s+\n/g, '\n')
    .replace(/\s{2,}/g, ' ')
    .replace(/[^\p{L}\p{N}\s.,!?;:'"()-]/gu, ' ')
    .replace(/\s{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\s+([\])}])/g, '$1')
    .replace(/([\[{])\s+/g, '$1')
    .trim();

  cleaned = cleaned.replace(/\s*([#*•>-])\s*/g, ' ');
  cleaned = cleaned.replace(/\s{2,}/g, ' ');
  cleaned = cleaned.replace(/\n {1,}/g, '\n');

  return cleaned.trim();
}

function compressPromptText(text, level = 'balanced', preserveEntities = true, customKeywords = []) {
  if (!text) return { compressedText: "", prunedWords: [] };
  let workingText = text;
  const protectedMap = new Map();
  let blockCounter = 0;
  const prunedWords = new Set();

  // 1. Protect Markdown code blocks
  workingText = workingText.replace(/```[\s\S]*?```/g, (match) => {
    const id = `__CODE_BLOCK_${blockCounter++}__`;
    protectedMap.set(id, match);
    return id;
  });

  // 2. Protect Inline Code
  workingText = workingText.replace(/`[^`]+`/g, (match) => {
    const id = `__INLINE_CODE_${blockCounter++}__`;
    protectedMap.set(id, match);
    return id;
  });

  // 3. Protect URLs
  workingText = workingText.replace(/https?:\/\/[^\s]+/g, (match) => {
    const id = `__URL_${blockCounter++}__`;
    protectedMap.set(id, match);
    return id;
  });

  // 4. Protect Emails
  workingText = workingText.replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, (match) => {
    const id = `__EMAIL_${blockCounter++}__`;
    protectedMap.set(id, match);
    return id;
  });

  // 5. Protect Custom Keywords
  if (Array.isArray(customKeywords) && customKeywords.length > 0) {
    customKeywords.forEach(keyword => {
      if (!keyword) return;
      const escKeyword = keyword.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
      const regex = new RegExp(`\\b${escKeyword}\\b`, 'gi');
      workingText = workingText.replace(regex, (match) => {
        const id = `__KEYWORD_${blockCounter++}__`;
        protectedMap.set(id, match);
        return id;
      });
    });
  }

  // 6. Protect Named Entities (Capitalized words like names, acronyms)
  if (preserveEntities) {
    workingText = workingText.replace(/\b[A-Z][a-zA-Z0-9]+\b/g, (match) => {
      if (match === 'I' || match === 'A' || match === 'IT') return match;
      const id = `__ENTITY_${blockCounter++}__`;
      protectedMap.set(id, match);
      return id;
    });
  }

  // 7. Prune Filler Phrases
  FILLER_PHRASES.forEach(regex => {
    workingText = workingText.replace(regex, (match) => {
      match.split(/\s+/).forEach(w => {
        const clean = w.toLowerCase().replace(/[^a-zA-Z0-9']+/g, '');
        if (clean) prunedWords.add(clean);
      });
      return '';
    });
  });

  // 8. Prune Conversational Noise
  CONVERSATIONAL_NOISE.forEach(regex => {
    workingText = workingText.replace(regex, (match) => {
      match.split(/\s+/).forEach(w => {
        const clean = w.toLowerCase().replace(/[^a-zA-Z0-9']+/g, '');
        if (clean) prunedWords.add(clean);
      });
      return '';
    });
  });

  // 9. Sentence-level similarity / Redundancy filter
  let parts = workingText.split(/([.!?]+\s+)/);
  let uniqueSentences = [];
  let acceptedSets = [];

  for (let i = 0; i < parts.length; i += 2) {
    const current = parts[i];
    const whitespace = parts[i + 1] || '';

    if (!current.trim()) {
      uniqueSentences.push(current + whitespace);
      continue;
    }

    let isRedundant = false;
    const currentTokens = current.toLowerCase().split(/[^a-zA-Z0-9_]+/);
    const currentSet = new Set(currentTokens.filter(t => t && !t.startsWith('__')));

    if (currentSet.size > 0) {
      // Limit to last 50 sentences to avoid O(N^2) lag on massive documents
      const recentSets = acceptedSets.slice(-50);
      for (let acceptedSet of recentSets) {
        let intersection = 0;
        currentSet.forEach(token => {
          if (acceptedSet.has(token)) intersection++;
        });
        
        const union = currentSet.size + acceptedSet.size - intersection;
        const similarity = intersection / union;

        const threshold = level === 'conservative' ? 0.85 : level === 'balanced' ? 0.70 : 0.55;
        if (similarity > threshold) {
          isRedundant = true;
          currentTokens.forEach(t => {
            if (t && !t.startsWith('__')) prunedWords.add(t);
          });
          break;
        }
      }
    }

    if (!isRedundant) {
      if (currentSet.size > 0) acceptedSets.push(currentSet);
      uniqueSentences.push(current + whitespace);
    }
  }

  workingText = uniqueSentences.join('');

  // 10. Stopword pruning (Aggressive only)
  if (level === 'aggressive') {
    let words = workingText.split(/(\s+)/);
    let compressedWords = words.map(token => {
      const clean = token.toLowerCase().replace(/[^a-zA-Z0-9']+/g, '');
      if (STOPWORDS.has(clean) && !token.startsWith('__')) {
        prunedWords.add(clean);
        return '';
      }
      return token;
    });
    workingText = compressedWords.join('');
  }

  // 11. Whitespace cleanup
  workingText = workingText.replace(/[ \t]+/g, ' ').replace(/\n{2,}/g, '\n').replace(/ ([.!?])/g, '$1').trim();

  // 12. Restore placeholders
  workingText = workingText.replace(/__(?:CODE_BLOCK|INLINE_CODE|URL|EMAIL|KEYWORD|ENTITY)_\d+__/g, (match) => {
    return protectedMap.has(match) ? protectedMap.get(match) : match;
  });

  return {
    compressedText: workingText,
    prunedWords: Array.from(prunedWords)
  };
}

// Injects values into standard input elements and contenteditables, triggering frameworks' reactivity
function setInputValue(element, value) {
  element.focus();
  if (element.tagName === 'TEXTAREA' || element.tagName === 'INPUT') {
    element.value = value;
    // Trigger DOM events for framework listener reactivity
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  } else if (element.getAttribute('contenteditable') === 'true') {
    try {
      // Clear existing selection and select all content in this editable element
      const range = document.createRange();
      range.selectNodeContents(element);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      
      // Replace selected text using insertText command (best for React/ProseMirror/Lexical)
      if (document.execCommand('insertText', false, value)) {
        // insertText naturally fires input events. Do NOT fire extra ones or it will crash Lexical.
      } else {
        element.innerText = value;
        // Dispatch input and change events for framework listeners manually if fallback is used
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
      }
    } catch (e) {
      console.error("TokenTrim: insertText execCommand failed, falling back to innerText", e);
      element.innerText = value;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }
}

// Find the active textbox or fallback
function findActiveInput() {
  const active = document.activeElement;
  if (active && (active.tagName === 'TEXTAREA' || active.getAttribute('contenteditable') === 'true')) {
    return active;
  }

  // Chat interface fallbacks
  // ChatGPT / OpenAI
  const chatgptInput = document.querySelector('#prompt-textarea');
  if (chatgptInput) return chatgptInput;

  // Claude.ai
  const claudeInput = document.querySelector('div[contenteditable="true"][data-testid="keep-markdown-editor"]');
  if (claudeInput) return claudeInput;

  // Gemini.google.com
  const geminiInput = document.querySelector('div[contenteditable="true"][role="textbox"]');
  if (geminiInput) return geminiInput;

  // Generic selectors
  const genericTextarea = document.querySelector('textarea');
  if (genericTextarea) return genericTextarea;

  const genericEditable = document.querySelector('div[contenteditable="true"]');
  if (genericEditable) return genericEditable;

  return null;
}

// Message Listener from Popup script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'compress') {
    const inputElement = findActiveInput();
    if (!inputElement) {
      sendResponse({ status: 'error', message: 'No input area detected. Click inside a text box first.' });
      return;
    }

    let originalText = '';
    if (request.text !== undefined && request.text !== null) {
      originalText = request.text;
    } else {
      originalText = inputElement.tagName === 'TEXTAREA' ? inputElement.value : inputElement.innerText;
    }

    if (!originalText || originalText.trim() === '') {
      sendResponse({ status: 'error', message: 'Prompt text is empty.' });
      return;
    }

    try {
      const { compressedText, prunedWords } = compressPromptText(
        originalText,
        request.level,
        request.preserveEntities,
        request.customKeywords
      );
      
      setInputValue(inputElement, compressedText);

      sendResponse({
        status: 'success',
        originalText: originalText,
        compressedText: compressedText,
        originalLength: originalText.length,
        compressedLength: compressedText.length,
        prunedWords: prunedWords
      });
    } catch (e) {
      sendResponse({ status: 'error', message: 'Compression failed: ' + e.message });
    }
  } else if (request.action === 'upload_files') {
    try {
      const files = request.files.map(f => base64ToFile(f.base64, f.name, f.type));
      const success = injectFiles(files);
      if (success) {
        sendResponse({ status: 'success', message: `Uploaded ${files.length} compressed files.` });
      } else {
        sendResponse({ status: 'error', message: 'Could not find attachment input on the page. Please ensure you are on a supported chat page.' });
      }
    } catch (e) {
      sendResponse({ status: 'error', message: 'File upload injection failed: ' + e.message });
    }
  } else if (request.action === 'ping') {
    // Ping to check if script is active
    sendResponse({ status: 'pong', url: window.location.href });
  }
  return true; // Keep message channel open for async response
});

// Helper: Convert Base64 back to File object
function base64ToFile(base64, filename, mimeType) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], { type: mimeType });
  return new File([blob], filename, { type: mimeType });
}

// Helper: Find attachment input and inject files
function injectFiles(files) {
  // Find all file inputs on page
  const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
  
  // Find input that accepts images, pdfs, or general files
  let targetInput = fileInputs.find(input => {
    const accept = input.getAttribute('accept') || '';
    return accept.includes('image') || accept.includes('*') || accept.includes('pdf') || accept.includes('video');
  }) || fileInputs[0];
  
  if (!targetInput) {
    // Fallback: dispatch drag-and-drop drop event on the active text area
    const chatInput = findActiveInput();
    if (chatInput) {
      const dataTransfer = new DataTransfer();
      files.forEach(file => dataTransfer.items.add(file));
      
      const dropEvent = new DragEvent('drop', {
        bubbles: true,
        cancelable: true,
        dataTransfer: dataTransfer
      });
      chatInput.dispatchEvent(dropEvent);
      return true;
    }
    return false;
  }
  
  const dataTransfer = new DataTransfer();
  files.forEach(file => dataTransfer.items.add(file));
  
  targetInput.files = dataTransfer.files;
  targetInput.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}

// --- MEDIA & PDF PARSERS ---
async function extractTextFromPDF(file) {
  try {
    if (typeof pdfjsLib === 'undefined') throw new Error("PDF.js library failed to load.");
    pdfjsLib.GlobalWorkerOptions.workerSrc = chrome.runtime.getURL('pdf.worker.min.js');
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    let fullText = '';
    const maxPages = Math.min(pdf.numPages, 100);
    for (let i = 1; i <= maxPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      const pageText = textContent.items.map(item => item.str).join(' ');
      fullText += pageText + '\n';
    }
    return fullText;
  } catch (e) {
    console.error("TokenTrim PDF Parsing error:", e);
    throw e;
  }
}

function estimateImageTokens(width, height) {
  let w = width;
  let h = height;
  if (w > 2048 || h > 2048) {
    const ratio = Math.min(2048 / w, 2048 / h);
    w = Math.round(w * ratio);
    h = Math.round(h * ratio);
  }
  const minDim = Math.min(w, h);
  if (minDim > 768) {
    const ratio = 768 / minDim;
    w = Math.round(w * ratio);
    h = Math.round(h * ratio);
  }
  const tilesW = Math.ceil(w / 512);
  const tilesH = Math.ceil(h / 512);
  return (tilesW * tilesH) * 170 + 85;
}

function compressImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectURL = URL.createObjectURL(file);
    img.src = objectURL;
    img.onload = () => {
      let w = img.width;
      let h = img.height;
      const maxDim = 512;
      if (w > maxDim || h > maxDim) {
        if (w > h) { h = Math.round((h * maxDim) / w); w = maxDim; }
        else { w = Math.round((w * maxDim) / h); h = maxDim; }
      }
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, w, h);
      canvas.toBlob((blob) => {
        const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, "_optimized.jpg"), { type: 'image/jpeg' });
        URL.revokeObjectURL(objectURL);
        resolve({ file: compressedFile });
      }, 'image/jpeg', 0.6);
    };
    img.onerror = () => { URL.revokeObjectURL(objectURL); reject(new Error("Image load failed.")); };
  });
}

function extractVideoFrames(file, maxFrames = 15) {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.muted = true;
    video.playsInline = true;
    const fileURL = URL.createObjectURL(file);
    video.src = fileURL;
    video.onloadedmetadata = () => {
      const duration = video.duration;
      let targetFrames = maxFrames;
      if (duration < 10) targetFrames = Math.min(10, Math.ceil(duration));
      const interval = duration / targetFrames;
      const files = [];
      let currentFrame = 0;
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      function seekAndCapture() {
        if (currentFrame >= targetFrames) {
          URL.revokeObjectURL(fileURL);
          resolve({ files: files });
          return;
        }
        video.currentTime = Math.min(currentFrame * interval, duration - 0.1);
      }
      
      video.onseeked = () => {
        let w = video.videoWidth || 640;
        let h = video.videoHeight || 480;
        const maxDim = 512;
        if (w > maxDim || h > maxDim) {
          if (w > h) { h = Math.round((h * maxDim) / w); w = maxDim; }
          else { w = Math.round((w * maxDim) / h); h = maxDim; }
        }
        canvas.width = w;
        canvas.height = h;
        ctx.drawImage(video, 0, 0, w, h);
        canvas.toBlob((blob) => {
          const frameFile = new File([blob], `${file.name.replace(/\.[^/.]+$/, "")}_frame_${currentFrame + 1}.jpg`, { type: 'image/jpeg' });
          files.push(frameFile);
          currentFrame++;
          seekAndCapture();
        }, 'image/jpeg', 0.55);
      };
      video.onerror = () => { URL.revokeObjectURL(fileURL); reject(new Error("Video timeline error.")); };
      seekAndCapture();
    };
    video.onerror = () => { URL.revokeObjectURL(fileURL); reject(new Error("Video load error.")); };
  });
}

// Processor factory
async function processNativeFiles(fileList) {
  const dt = new DataTransfer();
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (fileExt === '.pdf') {
      const text = await extractTextFromPDF(file);
      const { compressedText } = compressPromptText(text, 'balanced', true, []);
      const blob = new Blob([compressedText], { type: 'text/plain' });
      const newFile = new File([blob], file.name.replace(/\.pdf$/i, '_optimized.txt'), { type: 'text/plain' });
      dt.items.add(newFile);
    } else if (file.type.startsWith('image/')) {
      const res = await compressImage(file);
      dt.items.add(res.file);
    } else if (file.type.startsWith('video/')) {
      const res = await extractVideoFrames(file);
      res.files.forEach(f => dt.items.add(f));
    } else if (file.name.match(/\.(txt|md|json|csv|py|js|html|css|yaml|yml|cpp|java|xml|sh|env|ts|tsx)$/i) || file.type.startsWith('text/')) {
      const text = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.readAsText(file);
      });
      const { compressedText } = compressPromptText(text, 'balanced', true, []);
      const blob = new Blob([compressedText], { type: file.type || 'text/plain' });
      const newFile = new File([blob], file.name.replace(/(\.[^.]+)$/, '_optimized$1'), { type: file.type || 'text/plain' });
      dt.items.add(newFile);
    } else {
      // Unrecognized binaries (like .docx, .zip) pass through as is, uncompressed to avoid corruption
      dt.items.add(file);
    }
  }
  return dt;
}

// --- NATIVE FILE UPLOAD INTERCEPTOR ---
let isTokenTrimHandlingUpload = false;

document.addEventListener('change', async (e) => {
  if (e.target.type === 'file' && e.target.files && e.target.files.length > 0) {
    if (isTokenTrimHandlingUpload) {
      isTokenTrimHandlingUpload = false;
      return;
    }
    e.preventDefault();
    e.stopImmediatePropagation();
    e.stopPropagation();

    try {
      const newDt = await processNativeFiles(e.target.files);
      e.target.files = newDt.files;
    } catch(err) {
      console.error("TokenTrim native intercept error:", err);
    }
    isTokenTrimHandlingUpload = true;
    e.target.dispatchEvent(new Event('change', { bubbles: true }));
  }
}, true);

document.addEventListener('drop', async (e) => {
  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    if (isTokenTrimHandlingUpload) {
      isTokenTrimHandlingUpload = false;
      return;
    }
    e.preventDefault();
    e.stopImmediatePropagation();
    e.stopPropagation();

    let newDt;
    try {
      newDt = await processNativeFiles(e.dataTransfer.files);
    } catch(err) {
      console.error("TokenTrim native drop error:", err);
      newDt = e.dataTransfer; // fallback
    }

    isTokenTrimHandlingUpload = true;
    const newDropEvent = new DragEvent('drop', {
      bubbles: true,
      cancelable: true,
      dataTransfer: newDt
    });
    e.target.dispatchEvent(newDropEvent);
  }
}, true);

// --- INLINE CHATBOX OPTIMIZE BUTTON ---
function injectOptimizeButton() {
  if (document.getElementById('tokentrim-floating-btn')) return;

  const btn = document.createElement('button');
  btn.id = 'tokentrim-floating-btn';
  btn.innerText = '✂ Optimize';
  btn.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 999999;
    background: #4f46e5;
    color: white;
    border: none;
    border-radius: 20px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    font-family: sans-serif;
  `;

  btn.addEventListener('mousedown', (e) => {
    e.preventDefault(); // Prevent button from stealing focus
  });

  btn.addEventListener('click', () => {
    let inputElement = findActiveInput();
    if (!inputElement) {
      alert("No active text input found. Click inside the chat box first.");
      return;
    }
    let originalText = '';
    if (inputElement.tagName === 'TEXTAREA') {
      originalText = inputElement.value;
    } else {
      originalText = inputElement.innerText;
    }
    
    if (!originalText || originalText.trim() === '') {
      return;
    }
    try {
      const { compressedText } = compressPromptText(originalText, 'balanced', true, []);
      const finalText = sanitizeOptimizedPrompt(compressedText);
      setInputValue(inputElement, finalText);
      btn.innerText = '✅ Optimized';
      setTimeout(() => btn.innerText = '✂ Optimize', 2000);
    } catch (e) {
      console.error(e);
      alert("Optimization failed");
    }
  });

  document.body.appendChild(btn);
}

// Apply the button to the page
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectOptimizeButton);
} else {
  injectOptimizeButton();
}
// Use a low-impact interval instead of a heavy subtree MutationObserver 
// to ensure the button persists during SPA navigations without freezing the page.
setInterval(injectOptimizeButton, 1500);
