document.addEventListener('DOMContentLoaded', () => {
  // Model rates from the dashboard
  const MODEL_RATES = {
    'gemini-1.5-pro': { input: 1.25, name: 'Gemini 1.5 Pro' },
    'gemini-1.5-flash': { input: 0.075, name: 'Gemini 1.5 Flash' },
    'gpt-4o': { input: 5.00, name: 'GPT-4o' },
    'gpt-4o-mini': { input: 0.15, name: 'GPT-4o-mini' },
    'claude-3-5-sonnet': { input: 3.00, name: 'Claude 3.5 Sonnet' },
    'claude-3-haiku': { input: 0.25, name: 'Claude 3 Haiku' }
  };

  // UI Elements
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');
  const levelSelect = document.getElementById('level');
  const modelSelect = document.getElementById('target-model');
  const customKeywordsInput = document.getElementById('custom-keywords');
  const preserveCheckbox = document.getElementById('preserve');
  const compressBtn = document.getElementById('btn-compress');
  const bannerMessage = document.getElementById('banner-message');
  
  // Status Badge elements
  const statusBadge = document.getElementById('status-badge');
  const statusText = document.getElementById('status-text');

  // Slider Elements
  const volumeSlider = document.getElementById('volume-slider');
  const volumeVal = document.getElementById('volume-val');

  // Analytics Elements
  const metricPercent = document.getElementById('metric-percent');
  const metricTokensRaw = document.getElementById('metric-tokens-raw');
  const metricDollars = document.getElementById('metric-dollars');
  const metricSpeedup = document.getElementById('metric-speedup');
  const metricFidelity = document.getElementById('metric-fidelity');
  const reductionProgressBar = document.getElementById('reduction-progress');

  // Diff Panel
  const diffContainer = document.getElementById('diff-container');

  // State cache for last compression result
  let lastResult = null;

  // --- 1. Tab Handler ---
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      
      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      const targetPanel = document.getElementById(`panel-${targetTab}`);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }
    });
  });

  // --- 2. Load & Save Settings ---
  function loadSettings() {
    levelSelect.value = localStorage.getItem('cc_level') || 'balanced';
    modelSelect.value = localStorage.getItem('cc_model') || 'gpt-4o';
    customKeywordsInput.value = localStorage.getItem('cc_keywords') || '';
    preserveCheckbox.checked = localStorage.getItem('cc_preserve') !== 'false';
    volumeSlider.value = localStorage.getItem('cc_volume') || '100000';
    updateVolumeDisplay(volumeSlider.value);
  }

  function saveSettings() {
    localStorage.setItem('cc_level', levelSelect.value);
    localStorage.setItem('cc_model', modelSelect.value);
    localStorage.setItem('cc_keywords', customKeywordsInput.value);
    localStorage.setItem('cc_preserve', preserveCheckbox.checked);
    localStorage.setItem('cc_volume', volumeSlider.value);
  }

  // Bind settings saving to element change events
  [levelSelect, modelSelect, customKeywordsInput, preserveCheckbox, volumeSlider].forEach(el => {
    el.addEventListener('change', () => {
      saveSettings();
      if (lastResult) {
        recalculateMetrics();
      }
    });
  });

  volumeSlider.addEventListener('input', () => {
    updateVolumeDisplay(volumeSlider.value);
    saveSettings();
    if (lastResult) {
      recalculateMetrics();
    }
  });

  function updateVolumeDisplay(val) {
    const valInK = Math.round(val / 1000);
    volumeVal.innerText = `${valInK}k requests/mo`;
  }

  // --- 3. Platform Awareness & Injection Verification ---
  async function checkActiveTab() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab) {
        setOfflineStatus("No Active Tab");
        return;
      }

      const url = tab.url || "";
      let platform = "unknown";
      
      if (url.includes("chatgpt.com") || url.includes("chat.openai.com")) {
        platform = "chatgpt";
      } else if (url.includes("claude.ai")) {
        platform = "claude";
      } else if (url.includes("gemini.google.com")) {
        platform = "gemini";
      }

      // Update UI badge based on platform
      statusBadge.className = 'status-badge'; // reset
      if (platform === 'chatgpt') {
        statusBadge.classList.add('status-chatgpt');
        statusText.innerText = 'ChatGPT active';
      } else if (platform === 'claude') {
        statusBadge.classList.add('status-claude');
        statusText.innerText = 'Claude active';
      } else if (platform === 'gemini') {
        statusBadge.classList.add('status-gemini');
        statusText.innerText = 'Gemini active';
      } else {
        setOfflineStatus("Unsupported site");
        compressBtn.disabled = true;
        showBanner("Navigate to ChatGPT, Claude, or Gemini to compress prompts.", "error");
        return;
      }

      // Verify if the content script is responsive
      chrome.tabs.sendMessage(tab.id, { action: 'ping' }, (response) => {
        if (chrome.runtime.lastError || !response || response.status !== 'pong') {
          // Content script not ready yet (needs page reload)
          statusText.innerText = 'Needs page reload';
          statusBadge.className = 'status-badge'; // reset styles to default (gray)
          showBanner("Please reload the chat page once to enable TokenTrim.", "error");
        } else {
          compressBtn.disabled = false;
          hideBanner();
        }
      });

    } catch (e) {
      console.error("TokenTrim: tab check failed", e);
      setOfflineStatus("Offline");
    }
  }

  function setOfflineStatus(msg) {
    statusBadge.className = 'status-badge';
    statusText.innerText = msg;
  }

  // --- 4. Core Metrics & Savings Calculations ---
  function recalculateMetrics() {
    if (!lastResult) return;

    const originalTokens = Math.ceil(lastResult.originalLength / 4);
    const compressedTokens = Math.ceil(lastResult.compressedLength / 4);
    const tokensSaved = Math.max(0, originalTokens - compressedTokens);
    const percentSaved = originalTokens > 0 ? Math.round((tokensSaved / originalTokens) * 100) : 0;

    // Estimate costs
    const level = levelSelect.value;
    const modelKey = modelSelect.value;
    const monthlyVolume = parseInt(volumeSlider.value) || 100000;
    const rate = MODEL_RATES[modelKey].input; // price per 1M input tokens

    const originalCost = (originalTokens * monthlyVolume / 1000000) * rate;
    const compressedCost = (compressedTokens * monthlyVolume / 1000000) * rate;
    const monthlySavings = Math.max(0, originalCost - compressedCost);

    // Compute Speedup Factor
    let speedup = 1.0;
    if (percentSaved > 0) {
      speedup = 1.0 + (percentSaved / 100) * 0.8;
    }

    // Compute Preservation Index
    let preservation = 100 - (percentSaved * 0.1);
    if (level === 'aggressive') preservation -= 5;
    preservation = Math.min(100, Math.max(70, preservation));

    // Update UI elements
    metricPercent.innerText = `${percentSaved}%`;
    metricTokensRaw.innerText = `${tokensSaved} tokens saved`;
    reductionProgressBar.style.width = `${percentSaved}%`;

    // Single prompt cost calculations
    const singleOriginalCost = (originalTokens / 1000000) * rate;
    const singleCompressedCost = (compressedTokens / 1000000) * rate;
    const singleSavings = Math.max(0, singleOriginalCost - singleCompressedCost);

    // Update single-prompt savings card
    const singleSavingsEl = document.getElementById('metric-single-savings');
    const singleBreakdownEl = document.getElementById('metric-single-breakdown');
    if (singleSavingsEl) {
      singleSavingsEl.innerText = `$${singleSavings.toFixed(6)}`;
    }
    if (singleBreakdownEl) {
      singleBreakdownEl.innerText = `Before: $${singleOriginalCost.toFixed(6)} | After: $${singleCompressedCost.toFixed(6)}`;
    }

    metricDollars.innerText = `$${monthlySavings.toFixed(2)}`;
    const breakdownEl = document.getElementById('metric-costs-breakdown');
    if (breakdownEl) {
      breakdownEl.innerText = `Before: $${originalCost.toFixed(2)} | After: $${compressedCost.toFixed(2)}`;
    }
    metricSpeedup.innerText = `${speedup.toFixed(2)}x`;
    metricFidelity.innerText = `${preservation.toFixed(1)}%`;
  }

  // --- 5. Visual Diff Rendering ---
  function renderVisualDiff(original, compressed, prunedWordsArray) {
    diffContainer.innerHTML = '';
    
    if (!original || !compressed) {
      diffContainer.innerHTML = `
        <div class="diff-placeholder">
          <span class="diff-placeholder-icon">✂</span>
          <span>No text compressed yet.</span>
        </div>`;
      return;
    }

    const origTokens = original.split(/(\s+)/);
    const compWordsSet = new Set(compressed.toLowerCase().split(/[^a-zA-Z0-9']+/).filter(Boolean));
    const prunedSet = new Set(prunedWordsArray.map(w => w.toLowerCase()));

    let fragment = document.createDocumentFragment();

    origTokens.forEach(token => {
      if (token.trim() === '') {
        fragment.appendChild(document.createTextNode(token));
        return;
      }

      // Check if word is pruned
      const cleanWord = token.toLowerCase().replace(/[^a-zA-Z0-9']+/g, '');
      const isPruned = cleanWord && !compWordsSet.has(cleanWord) && prunedSet.has(cleanWord);

      const span = document.createElement('span');
      if (isPruned) {
        span.className = 'diff-removed';
        span.innerText = token;
      } else {
        span.className = 'diff-preserved';
        span.innerText = token;
      }
      fragment.appendChild(span);
    });

    diffContainer.appendChild(fragment);
  }

  // --- 6. Banner Message Helpers ---
  function showBanner(text, type) {
    bannerMessage.innerText = text;
    bannerMessage.className = 'banner'; // clear classes
    
    if (type === 'error') {
      bannerMessage.classList.add('banner-error');
    } else {
      bannerMessage.classList.add('banner-success');
    }
    
    bannerMessage.style.display = 'flex';
  }

  function hideBanner() {
    bannerMessage.style.display = 'none';
  }

  // --- 7. Compression Action Button ---
  compressBtn.addEventListener('click', async () => {
    hideBanner();
    compressBtn.disabled = true;
    compressBtn.querySelector('span').innerText = 'Optimizing...';

    const level = levelSelect.value;
    const preserveEntities = preserveCheckbox.checked;
    const customKeywords = customKeywordsInput.value
      .split(',')
      .map(k => k.trim())
      .filter(k => k.length > 0);

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      showBanner("Could not find active tab.", "error");
      resetCompressBtn();
      return;
    }

    chrome.tabs.sendMessage(tab.id, {
      action: 'compress',
      level: level,
      preserveEntities: preserveEntities,
      customKeywords: customKeywords
    }, (response) => {
      resetCompressBtn();

      if (chrome.runtime.lastError) {
        showBanner("Make sure the page is loaded and click inside the text area first.", "error");
        return;
      }

      if (response && response.status === 'success') {
        // Cache result
        lastResult = response;

        // Recalculate metrics
        recalculateMetrics();

        // Render diff view
        renderVisualDiff(response.originalText, response.compressedText, response.prunedWords);

        // Show banner success
        showBanner(`Successfully compressed input!`, "success");

        // Automatically click to Analytics tab to show achievements
        document.getElementById('tab-analytics-btn').click();
      } else {
        showBanner(response ? response.message : "Active text input area not found.", "error");
      }
    });
  });

  function resetCompressBtn() {
    compressBtn.disabled = false;
    compressBtn.querySelector('span').innerText = 'Compress Active Input';
  }

  // --- 8. Document/Media Upload Handling ---
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('doc-file');
  const uploadStatusText = document.getElementById('upload-status-text');

  // Trigger file input when drop zone clicked
  dropZone.addEventListener('click', () => {
    fileInput.click();
  });

  // Drag and drop event listeners
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUploadedFile(e.dataTransfer.files[0]);
    }
  });

  // File selection event listener
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleUploadedFile(e.target.files[0]);
    }
  });

  async function handleUploadedFile(file) {
    const fileName = file.name;
    const fileExt = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
    
    uploadStatusText.innerText = `Processing: ${fileName}...`;
    hideBanner();

    try {
      if (fileExt === '.pdf') {
        uploadStatusText.innerText = `Extracting PDF text...`;
        const text = await extractTextFromPDF(file);
        if (!text || text.trim() === '') {
          throw new Error("Could not extract any text from this PDF document.");
        }
        uploadStatusText.innerText = `Compressing text...`;
        await compressFileContent(text, fileName);
      } else if (file.type.startsWith('image/')) {
        uploadStatusText.innerText = `Compressing image...`;
        const compressedImage = await compressImage(file);
        uploadStatusText.innerText = `Uploading image...`;
        await uploadCompressedFiles([compressedImage.file], compressedImage.metrics, fileName);
      } else if (file.type.startsWith('video/')) {
        uploadStatusText.innerText = `Extracting keyframes...`;
        const result = await extractVideoFrames(file);
        uploadStatusText.innerText = `Uploading keyframes...`;
        await uploadCompressedFiles(result.files, result.metrics, fileName);
      } else {
        const text = await readTextFile(file);
        uploadStatusText.innerText = `Compressing text...`;
        await compressFileContent(text, fileName);
      }
    } catch (err) {
      showBanner(`Error processing ${fileName}: ${err.message}`, "error");
      uploadStatusText.innerText = "Click or Drag File to Upload";
    }
  }

  // Helper: Read standard text file
  function readTextFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = () => reject(new Error("Failed to read text file."));
      reader.readAsText(file);
    });
  }

  // Helper: Extract text from PDF using pdf.js
  async function extractTextFromPDF(file) {
    try {
      if (typeof pdfjsLib !== 'undefined') {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'pdf.worker.min.js';
      } else {
        throw new Error("PDF.js library failed to load in the extension.");
      }
      
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
      console.error("PDF Parsing error:", e);
      throw new Error("PDF parser failed. Ensure the PDF contains readable text.");
    }
  }

  // Helper: Compress Image to max 512px (LLM Low-Res mode) and high compression JPEG
  function compressImage(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const objectURL = URL.createObjectURL(file);
      img.src = objectURL;
      
      img.onload = () => {
        let w = img.width;
        let h = img.height;
        
        const originalTokens = estimateImageTokens(w, h);
        
        const maxDim = 512;
        if (w > maxDim || h > maxDim) {
          if (w > h) {
            h = Math.round((h * maxDim) / w);
            w = maxDim;
          } else {
            w = Math.round((w * maxDim) / h);
            h = maxDim;
          }
        }
        
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        
        canvas.toBlob((blob) => {
          const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, "") + "_compressed.jpg", {
            type: 'image/jpeg'
          });
          
          URL.revokeObjectURL(objectURL);
          
          resolve({
            file: compressedFile,
            metrics: {
              originalTokens: originalTokens,
              compressedTokens: 85,
              originalDesc: `[Original Image: ${file.name} (${img.width}x${img.height})]`,
              compressedDesc: `[Compressed Image: ${compressedFile.name} (${w}x${h}) - 85 Tokens (Low-Res Mode)]`
            }
          });
        }, 'image/jpeg', 0.6);
      };
      
      img.onerror = () => {
        URL.revokeObjectURL(objectURL);
        reject(new Error("Failed to load image."));
      };
    });
  }

  // Helper: Extract Video Keyframes (e.g. max 15 frames)
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
        const originalTokens = Math.ceil(duration * 258);
        
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
            
            const compressedTokens = targetFrames * 85;
            resolve({
              files: files,
              metrics: {
                originalTokens: originalTokens,
                compressedTokens: compressedTokens,
                originalDesc: `[Original Video: ${file.name} (${duration.toFixed(1)}s)]`,
                compressedDesc: `[Compressed Video: Extracted ${targetFrames} keyframes (${targetFrames * 85} Tokens)]`
              }
            });
            return;
          }
          
          const time = currentFrame * interval;
          video.currentTime = Math.min(time, duration - 0.1);
        }
        
        video.onseeked = () => {
          let w = video.videoWidth || 640;
          let h = video.videoHeight || 480;
          
          const maxDim = 512;
          if (w > maxDim || h > maxDim) {
            if (w > h) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            } else {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }
          
          canvas.width = w;
          canvas.height = h;
          ctx.drawImage(video, 0, 0, w, h);
          
          canvas.toBlob((blob) => {
            const frameFile = new File([blob], `${file.name.replace(/\.[^/.]+$/, "")}_frame_${currentFrame + 1}.jpg`, {
              type: 'image/jpeg'
            });
            files.push(frameFile);
            currentFrame++;
            seekAndCapture();
          }, 'image/jpeg', 0.55);
        };
        
        video.onerror = (e) => {
          URL.revokeObjectURL(fileURL);
          reject(new Error("Failed to process video timeline."));
        };
        
        seekAndCapture();
      };
      
      video.onerror = (e) => {
        URL.revokeObjectURL(fileURL);
        reject(new Error("Failed to load video metadata."));
      };
    });
  }

  // Helper: Estimate image tokens based on GPT-4o tile rules
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

  // Helper: Convert File to Base64 (needed for cross-context passing)
  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = (error) => reject(error);
      reader.readAsDataURL(file);
    });
  }

  // Helper: Upload file list using page inject
  async function uploadCompressedFiles(fileList, metrics, originalName) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      showBanner("Could not find active tab to upload files.", "error");
      uploadStatusText.innerText = "Click or Drag File to Upload";
      return;
    }

    const serializedFiles = [];
    for (let file of fileList) {
      const b64 = await fileToBase64(file);
      serializedFiles.push({
        base64: b64,
        name: file.name,
        type: file.type
      });
    }

    chrome.tabs.sendMessage(tab.id, {
      action: 'upload_files',
      files: serializedFiles
    }, (response) => {
      uploadStatusText.innerText = "Click or Drag File to Upload";
      fileInput.value = '';

      if (chrome.runtime.lastError) {
        showBanner("Extension connection lost. Reload the chat tab once to re-initialize.", "error");
        return;
      }

      if (response && response.status === 'success') {
        lastResult = {
          status: 'success',
          originalText: metrics.originalDesc,
          compressedText: metrics.compressedDesc,
          originalLength: metrics.originalTokens * 4,
          compressedLength: metrics.compressedTokens * 4,
          prunedWords: ['high-resolution-overhead']
        };

        recalculateMetrics();

        renderVisualDiff(lastResult.originalText, lastResult.compressedText, lastResult.prunedWords);

        showBanner(`Successfully compressed and uploaded ${originalName}!`, "success");
        document.getElementById('tab-analytics-btn').click();
      } else {
        showBanner(response ? response.message : "Failed to upload files into active chat.", "error");
      }
    });
  }

  async function compressFileContent(text, fileName) {
    hideBanner();
    
    const level = levelSelect.value;
    const preserveEntities = preserveCheckbox.checked;
    const customKeywords = customKeywordsInput.value
      .split(',')
      .map(k => k.trim())
      .filter(k => k.length > 0);

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      showBanner("Could not find active tab to insert compressed document.", "error");
      uploadStatusText.innerText = "Click or Drag File to Upload";
      return;
    }

    uploadStatusText.innerText = "Optimizing and inserting...";

    chrome.tabs.sendMessage(tab.id, {
      action: 'compress',
      text: text,
      level: level,
      preserveEntities: preserveEntities,
      customKeywords: customKeywords
    }, (response) => {
      uploadStatusText.innerText = "Click or Drag File to Upload";
      fileInput.value = '';

      if (chrome.runtime.lastError) {
        showBanner("Make sure the page is loaded and click inside the text area first.", "error");
        return;
      }

      if (response && response.status === 'success') {
        lastResult = response;

        recalculateMetrics();

        renderVisualDiff(response.originalText, response.compressedText, response.prunedWords);

        showBanner(`Successfully compressed and injected ${fileName}!`, "success");

        document.getElementById('tab-analytics-btn').click();
      } else {
        showBanner(response ? response.message : "Active text input area not found.", "error");
      }
    });
  }

  // Option / Guide link click helper
  document.getElementById('link-options').addEventListener('click', (e) => {
    e.preventDefault();
    showBanner("TokenTrim isolates code blocks, URLs, emails, and entities before stripping redundancies and sentence similarities locally in your browser. All data remains private.", "success");
  });

  // Run initialization
  loadSettings();
  checkActiveTab();
});
