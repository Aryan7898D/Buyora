/* ============================================================
   BUYORA - Config
   Yahan backend ka address set hota hai.

   Jab site Python server (python run.py) se khulti hai, to ye file
   server khud "/api" ke saath bhej deta hai - kuch badalna nahi padta.

   Ye file tab kaam aati hai jab site kisi aur server se khule
   (jaise VS Code Live Server): tab API http://localhost:5000/api par dhundhi jati hai.
   Live deploy karte waqt isko apne backend ke URL se badal do.
   ============================================================ */
window.BUYORA_API_BASE = "http://localhost:5000/api";
