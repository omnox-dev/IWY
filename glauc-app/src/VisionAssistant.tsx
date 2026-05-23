import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as tf from '@tensorflow/tfjs';
import * as cocoSsd from '@tensorflow-models/coco-ssd';
import { createWorker } from 'tesseract.js';
import { TextToSpeech } from '@capacitor-community/text-to-speech';
import { Ocr } from '@capacitor-community/image-to-text';
import { CameraPreview } from '@capacitor-community/camera-preview';
import { Haptics, ImpactStyle, NotificationType } from '@capacitor/haptics';
import { Capacitor } from '@capacitor/core';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Detection = any;

const VisionAssistant: React.FC = () => {
  const [model, setModel] = useState<cocoSsd.ObjectDetection | null>(null);
  const [lastAnnounced, setLastAnnounced] = useState<string>('');
  const [isOCRMode, setIsOCRMode] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [, setIsScanning] = useState(false); 
  const [detections, setDetections] = useState<Detection[]>([]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const lastTapTime = useRef<number>(0);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ocrWorkerRef = useRef<any>(null);
  const singleTapTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isNative = Capacitor.isNativePlatform();

  const startCamera = useCallback(async () => {
    if (isNative) {
      try {
        document.body.style.backgroundColor = 'transparent';
        await CameraPreview.start({
          position: 'rear',
          toBack: true,
          disableAudio: true,
          className: 'camera-preview-class'
        });
      } catch (e) {
        console.error("Native Camera Preview failed:", e);
      }
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { facingMode: 'environment' } 
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (e) {
        console.error("Web Camera access failed:", e);
      }
    }
  }, [isNative]);

  const triggerHaptic = useCallback(async (type: 'impact' | 'notification' | 'selection' = 'impact') => {
    if (!isNative) return;
    try {
      if (type === 'impact') {
        await Haptics.impact({ style: ImpactStyle.Heavy });
      } else if (type === 'notification') {
        await Haptics.notification({ type: NotificationType.Success });
      } else {
        await Haptics.selectionStart();
      }
    } catch {
      console.warn("Haptics not supported");
    }
  }, [isNative]);

  const speak = useCallback(async (text: string, force: boolean = false) => {
    setLastAnnounced(text);
    try {
      if (force) {
        await TextToSpeech.stop();
      }
      await TextToSpeech.speak({
        text,
        lang: 'en-US',
        rate: 1.0,
        pitch: 1.0,
        volume: 1.0,
        category: 'ambient',
      });
    } catch {
      if (!isNative) {
        if (force) window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
      }
    }
  }, [isNative]);

  useEffect(() => {
    document.documentElement.style.backgroundColor = 'transparent';
    document.body.style.backgroundColor = 'transparent';
    
    const initAI = async () => {
      try {
        await tf.ready();
        const loadedModel = await cocoSsd.load();
        setModel(loadedModel);
        
        if (!isNative) {
          const worker = await createWorker('eng');
          ocrWorkerRef.current = worker;
        }
        
        setIsInitialized(true);
        await speak("System active in background. Tap to scan. Double tap to switch mode.", true);
      } catch (e) {
        console.error("AI Init failed", e);
      }
    };

    initAI();
    startCamera();

    const currentVideo = videoRef.current;
    return () => {
      if (isNative) {
        CameraPreview.stop();
      } else if (currentVideo?.srcObject) {
        const stream = currentVideo.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
      if (ocrWorkerRef.current) {
        ocrWorkerRef.current.terminate();
      }
    };
  }, [isNative, startCamera, speak]);

  const captureFrame = async (): Promise<{ element: HTMLCanvasElement, width: number, height: number } | null> => {
    let imageElement: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement | null = null;
    let imgWidth = 0;
    let imgHeight = 0;

    if (isNative) {
      const result = await CameraPreview.capture({ quality: isOCRMode ? 90 : 50 });
      const img = new Image();
      img.src = `data:image/jpeg;base64,${result.value}`;
      await new Promise(resolve => img.onload = resolve);
      imageElement = img;
      imgWidth = img.width;
      imgHeight = img.height;
    } else if (videoRef.current) {
      imageElement = videoRef.current;
      imgWidth = videoRef.current.videoWidth;
      imgHeight = videoRef.current.videoHeight;
    }

    if (!imageElement || imgWidth === 0) return null;

    const canvas = document.createElement('canvas');
    canvas.width = imgWidth;
    canvas.height = imgHeight;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(imageElement, 0, 0, imgWidth, imgHeight);
      return { element: canvas, width: imgWidth, height: imgHeight };
    }
    return null;
  };

  const triggerEnvironmentScan = async () => {
    if (!model) return;
    setIsScanning(true);
    setDetections([]);
    await triggerHaptic('selection');
    
    try {
      const frameData = await captureFrame();
      if (!frameData) {
        setIsScanning(false);
        return;
      }
      
      const { element, width, height } = frameData;
      const predictions = await model.detect(element);
      const topPredictions = predictions.filter(p => p.score > 0.50);

      if (topPredictions.length === 0) {
        await speak("No clear objects detected.", true);
        setIsScanning(false);
        return;
      }

      // Map bounding boxes for UI rendering
      const mappedDetections = topPredictions.map(p => ({
        class: p.class,
        left: (p.bbox[0] / width) * 100,
        top: (p.bbox[1] / height) * 100,
        width: (p.bbox[2] / width) * 100,
        height: (p.bbox[3] / height) * 100,
      }));
      setDetections(mappedDetections);
      // Clear highlights after 6 seconds
      setTimeout(() => setDetections([]), 6000);

      // Grouping and spatial calculation
      const objectCounts: { [key: string]: { count: number, details: string[] } } = {};

      topPredictions.forEach(p => {
        const [x, _y, wBox, hBox] = p.bbox;
        const areaRatio = (wBox * hBox) / (width * height);
        const centerX = x + wBox / 2;
        const posRatio = centerX / width;
        
        let distance = "far";
        if (areaRatio > 0.35) distance = "very close";
        else if (areaRatio > 0.15) distance = "near";

        let direction = "in the center";
        if (posRatio < 0.35) direction = "on your left";
        else if (posRatio > 0.65) direction = "on your right";

        if (!objectCounts[p.class]) {
          objectCounts[p.class] = { count: 0, details: [] };
        }
        objectCounts[p.class].count += 1;
        objectCounts[p.class].details.push(`${distance} ${direction}`);
      });

      let descriptionParts: string[] = [];
      for (const [obj, data] of Object.entries(objectCounts)) {
        if (data.count === 1) {
          descriptionParts.push(`one ${obj} ${data.details[0]}`);
        } else {
          descriptionParts.push(`${data.count} ${obj}s, including one ${data.details[0]}`);
        }
      }

      const finalDescription = `I see ${descriptionParts.join(' and ')}.`;
      await speak(finalDescription, true);

    } catch (e) {
      console.error(e);
      await speak("Error scanning environment.", true);
    }
    setIsScanning(false);
  };

  const triggerOCRScan = async () => {
    setIsScanning(true);
    setDetections([]);
    await triggerHaptic('selection');
    await speak("Scanning for text...", true);
    
    try {
      let rawText = "";
      if (isNative) {
        const result = await CameraPreview.capture({ quality: 90 });
        if (!result.value) throw new Error("No image data captured");
        const ocrResult = await Ocr.detectText({ base64: result.value });
        rawText = ocrResult.textDetections.map((d: any) => d.text).join(' ');
      } else {
        if (!ocrWorkerRef.current) return;
        const frameData = await captureFrame();
        if (frameData) {
          const { data: { text } } = await ocrWorkerRef.current.recognize(frameData.element);
          rawText = text;
        }
      }

      let cleaned = rawText.replace(/[^A-Za-z0-9 '"\-.,!?()]/g, ' ');
      cleaned = cleaned.replace(/\s+/g, ' ').trim();

      if (cleaned.length > 3) {
        await triggerHaptic('notification');
        await speak(`Found text: ${cleaned}`, true);
      } else {
        await speak("No text found. Try adjusting camera.", true);
      }
    } catch (e) {
      console.error(e);
      await speak("Error reading text.", true);
    }
    setIsScanning(false);
  };

  const handleInteraction = () => {
    if (!isInitialized) return;
    
    const now = Date.now();
    const DOUBLE_TAP_DELAY = 300;

    if (now - lastTapTime.current < DOUBLE_TAP_DELAY) {
      if (singleTapTimeout.current) clearTimeout(singleTapTimeout.current);
      const newMode = !isOCRMode;
      setIsOCRMode(newMode);
      setDetections([]); // Clear edge traces on switch
      triggerHaptic('impact');
      speak(newMode ? "Reading mode ready" : "Safety mode ready", true);
    } else {
      singleTapTimeout.current = setTimeout(() => {
        if (isOCRMode) {
          triggerOCRScan();
        } else {
          triggerEnvironmentScan();
        }
      }, DOUBLE_TAP_DELAY + 50);
    }
    lastTapTime.current = now;
  };

  return (
    <div 
      className="w-full h-full relative overflow-hidden bg-transparent select-none font-mono"
      onPointerDown={handleInteraction}
      role="main"
    >
      {!isNative && (
        <video 
          ref={videoRef} 
          autoPlay 
          playsInline 
          className="absolute inset-0 w-full h-full object-cover z-0"
        />
      )}

      {/* Dark overlay to simulate scanner look */}
      <div 
        className="absolute inset-0 z-10 pointer-events-none transition-colors duration-300"
        style={{ backgroundColor: isOCRMode ? 'rgba(0,0,0,0.6)' : 'rgba(0,0,0,0.3)' }}
      ></div>

      {/* Mode Indicator (Top Left) */}
      <div className="absolute top-10 left-5 z-20 pointer-events-none">
        <div className="text-[#eaea00] text-[16px] font-bold tracking-wide">
          {isOCRMode ? "TEXT SCAN (OCR)" : "EDGE-ENHANCEMENT"}
        </div>
      </div>

      {/* Central Reticle */}
      <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
        <div className="relative w-32 h-32">
          {/* Circle */}
          <div className="absolute inset-0 rounded-full border border-[#006464]"></div>
          {/* Crosshairs */}
          <div className="absolute top-1/2 -left-4 w-8 h-[1.5px] bg-[#eaea00]"></div>
          <div className="absolute top-1/2 -right-4 w-8 h-[1.5px] bg-[#eaea00]"></div>
          <div className="absolute left-1/2 -top-4 w-[1.5px] h-8 bg-[#eaea00]"></div>
          <div className="absolute left-1/2 -bottom-4 w-[1.5px] h-8 bg-[#eaea00]"></div>
        </div>
      </div>

      {/* OCR Guide Box */}
      {isOCRMode && (
        <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
          <div className="w-[60%] h-[25%] border-2 border-[#eaea00] relative">
            <div className="absolute -top-6 left-0 text-[#eaea00] text-sm">
              Align Text Here
            </div>
          </div>
        </div>
      )}

      {/* Bounding Boxes */}
      <div className="absolute inset-0 z-20 pointer-events-none">
        {detections.map((d, i) => (
          <div 
            key={i} 
            className="absolute border-2 border-[#eaea00]"
            style={{
              left: `${d.left}%`,
              top: `${d.top}%`,
              width: `${d.width}%`,
              height: `${d.height}%`
            }}
          >
            <div className="absolute -top-6 left-0 bg-[#eaea00] text-black text-[11px] font-bold px-1.5 h-6 flex items-center uppercase whitespace-nowrap">
              {d.class}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Status Bar */}
      <div className="absolute bottom-0 left-0 right-0 h-[70px] bg-black/70 z-20 pointer-events-none flex flex-col justify-center px-5 border-t border-[#eaea00]/10">
        <div className="text-white text-[13px] mb-1 truncate">
          STATUS: {lastAnnounced || "System Ready"}
        </div>
        <div className="text-[#eaea00] text-[11px]">
          DOUBLE-CLICK: Switch Mode | SINGLE-CLICK: Scan
        </div>
      </div>
    </div>
  );
};

export default VisionAssistant;
