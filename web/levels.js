// Daftar level/badge EduTrash, berdasarkan total poin.
// Dipake bareng di beranda.html, profil.html, dll.
//
// CATATAN PENTING: kalau daftar LEVELS ini diubah (nama/ambang batas poin),
// samain juga LEVELS di ai/app.py biar badge yang dikasih backend pas
// scan konsisten sama yang ditampilin di sini.

const LEVELS = [
  { name: "Pemula Peduli", emoji: "🌱", minPoints: 0 },
  { name: "Pemilah Sampah", emoji: "🗑️", minPoints: 20 },
  { name: "Ksatria Daur Ulang", emoji: "♻️", minPoints: 50 },
  { name: "Pahlawan Sampah", emoji: "🦸", minPoints: 100 },
  { name: "Pejuang Lingkungan", emoji: "🌍", minPoints: 200 },
  { name: "Master Pemilah", emoji: "🏅", minPoints: 350 },
  { name: "Duta Lingkungan", emoji: "🌿", minPoints: 550 },
  { name: "Legenda Daur Ulang", emoji: "👑", minPoints: 800 },
  { name: "Penyelamat Bumi", emoji: "🌏", minPoints: 1200 },
  { name: "EduTrash Grandmaster", emoji: "🏆", minPoints: 1700 }
];

function getLevelInfo(points) {
  points = points || 0;
  let current = LEVELS[0];
  let next = null;

  for (let i = 0; i < LEVELS.length; i++) {
    if (points >= LEVELS[i].minPoints) {
      current = LEVELS[i];
      next = LEVELS[i + 1] || null;
    }
  }

  const progressPercent = next
    ? Math.round(((points - current.minPoints) / (next.minPoints - current.minPoints)) * 100)
    : 100;

  return {
    name: current.name,
    emoji: current.emoji,
    points,
    next,
    pointsToNext: next ? next.minPoints - points : 0,
    progressPercent
  };
}

function renderLevelBadgeHTML(points) {
  const info = getLevelInfo(points);
  return `${info.emoji} ${info.name}`;
}

function renderProgressBarHTML(points) {
  const info = getLevelInfo(points);
  if (!info.next) {
    return `<div style="margin-top:6px; font-size:13px; color:#ffd54f;">🏆 Level maksimal tercapai!</div>`;
  }
  return `
    <div style="margin-top:6px;">
      <div style="background:#333; border-radius:6px; height:8px; overflow:hidden;">
        <div style="background:#4caf50; height:100%; width:${info.progressPercent}%;"></div>
      </div>
      <div style="font-size:12px; color:#999; margin-top:4px;">${info.pointsToNext} poin lagi menuju ${info.next.emoji} ${info.next.name}</div>
    </div>
  `;
}

function renderRoadmapHTML(points) {
  const currentName = getLevelInfo(points).name;
  return LEVELS.map(lvl => {
    const unlocked = points >= lvl.minPoints;
    const isCurrent = lvl.name === currentName;
    return `
      <div style="display:flex; align-items:center; justify-content:space-between;
                  padding:8px 0; border-bottom:1px solid #333;
                  opacity:${unlocked ? "1" : "0.4"};">
        <span>${lvl.emoji} ${lvl.name}${isCurrent ? ' <span style="color:#4caf50;">(kamu di sini)</span>' : ""}</span>
        <span style="font-size:13px; color:#999;">${lvl.minPoints}+ poin</span>
      </div>
    `;
  }).join("");
}