/* audio-index.js — 学写字 · Character Studio · audio manifest (OPTIONAL).
   Lists which recordings actually exist on disk so the app plays a real file
   when it has one and silently uses the browser's Chinese text-to-speech
   (read-aloud) for everything else — never firing a 404 for a missing file.

   How playback decides (see playAudio in app.js):
     1. window.AUDIO_INDEX[kind][key] === true  → play  audio/<kind>/<key>.mp3
     2. otherwise                                → speak <key> with zh-CN TTS

   kind is one of: "char" | "word" | "sentence".
   key  is the exact text: the Hanzi ("人"), the word ("人口"), or the full
        sentence string with punctuation ("张口说"你好"。").

   ▸ Teacher / Claude Code workflow when real audio arrives:
       1. Drop files at audio/char/人.mp3, audio/word/人口.mp3, audio/sentence/<text>.mp3
          (filenames are URL-encoded automatically by the app).
       2. Flip the matching entry here to true (or generate this whole file from
          the contents of the audio/ folders).
     Until then, leaving this empty means EVERYTHING is read aloud by the browser,
     which is the intended fallback — the app is fully usable with zero audio files.

   Example once recordings exist:
       window.AUDIO_INDEX = {
         char:     { "人": true, "口": true },
         word:     { "人口": true },
         sentence: { "张口说“你好”。": true }
       }; */
window.AUDIO_INDEX = {
  char: {},
  word: {},
  sentence: {}
};
