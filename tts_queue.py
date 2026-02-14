import threading
import queue
import time

try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    pyttsx3 = None
    TTS_AVAILABLE = False

_tts_queue = queue.PriorityQueue()
_worker_thread = None
_engine = None
_engine_lock = threading.Lock()
_INTERRUPT_PRIORITY = 2


def _worker():
    if not TTS_AVAILABLE:
        print("[TTS System]: pyttsx3 not available.")
        while True:
            _, item = _tts_queue.get()
            if item is None: break
            print(f"[TTS Fallback]: {item[0]}")
        return

    # On Windows, COM must be initialized in the thread
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except:
        pass

    while True:
        priority, item = _tts_queue.get()
        if item is None: break
        
        text, rate = item
        try:
            # Create a FRESH engine instance for every phrase
            # This is the ONLY way to guarantee sound on Windows after an interruption (engine.stop)
            # It prevents the engine from getting "stuck" in a silent state.
            engine = pyttsx3.init()
            engine.setProperty('rate', rate)
            engine.setProperty('volume', 1.0)
            
            # Use the first available voice
            voices = engine.getProperty('voices')
            if voices:
                engine.setProperty('voice', voices[0].id)

            print(f"[TTS System]: Hardware Output -> {text}")
            engine.say(text)
            engine.runAndWait()
            
            # Clean up engine immediately
            del engine
            
        except Exception as e:
            print(f"[TTS System]: Hardware Error: {e}")
            print(f"[TTS Fallback]: {text}")
            
        _tts_queue.task_done()


def _ensure_engine():
    global _worker_thread
    if _worker_thread is None:
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()


def speak(text, priority=5, rate=160):
    """Enqueue text for speaking. Lower priority number = higher priority."""
    if not text:
        return
    
    # Always print to console
    print(f"[TTS QUEUE]: P{priority} -> {text}")
    
    _ensure_engine()
    
    # For urgent messages (Priority 1 or 2), we clear the queue 
    # so the user doesn't hear out-of-date information.
    if priority <= _INTERRUPT_PRIORITY:
        try:
            while not _tts_queue.empty():
                _tts_queue.get_nowait()
                _tts_queue.task_done()
        except:
            pass
            
    _tts_queue.put((priority, (text, rate)))


def stop():
    _tts_queue.put((0, None))
    # Clear global engine
    global _engine
    with _engine_lock:
        _engine = None
