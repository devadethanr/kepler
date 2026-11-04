import React, { useEffect, useRef } from 'react';
import type { OfficeState } from '../../lib/research-office';
import { getCachedSprite } from './spriteCache';

type Role = 'analyst' | 'skeptic';
type Box = { x: number; y: number; width: number; height: number };
const WIDTH = 960;
const HEIGHT = 500;

/** One coordinate system drives both the drawing and accessible controls. */
export function officeLayout(scene: OfficeState): Record<Role, { character: Box; bubble: Box }> {
  const speaking = (role: Role) => scene.agents[role].state === 'speaking';
  return {
    analyst: {
      character: speaking('analyst') ? { x: 390, y: 258, width: 74, height: 110 } : { x: 153, y: 256, width: 74, height: 110 },
      bubble: speaking('analyst') ? { x: 265, y: 165, width: 210, height: 80 } : { x: 65, y: 155, width: 215, height: 80 },
    },
    skeptic: {
      character: speaking('skeptic') ? { x: 502, y: 258, width: 74, height: 110 } : { x: 733, y: 256, width: 74, height: 110 },
      bubble: speaking('skeptic') ? { x: 485, y: 165, width: 210, height: 80 } : { x: 680, y: 155, width: 215, height: 80 },
    },
  };
}

const rect = (ctx: CanvasRenderingContext2D, color: string, x: number, y: number, w: number, h: number) => {
  ctx.fillStyle = color; ctx.fillRect(x, y, w, h);
};

function drawOffice(ctx: CanvasRenderingContext2D) {
  const r = (c: string, x: number, y: number, w: number, h: number) => rect(ctx, c, x, y, w, h);
  r('#243b3b', 0, 0, 960, 500); r('#d6c7a9', 12, 12, 936, 226);
  r('#f1e4ca', 20, 20, 920, 196); r('#a77d5a', 20, 205, 920, 13);
  r('#be8a60', 12, 218, 936, 270); r('#d6a578', 20, 226, 920, 254);
  for (let y = 242; y < 480; y += 36) { r('#c49368', 20, y, 920, 3); for (let x = (y % 72 ? 100 : 200); x < 940; x += 200) r('#c49368', x, y - 15, 3, 15); }
  // Back wall windows and a board give the room depth.
  for (const x of [82, 738]) {
    r('#725c49', x, 45, 138, 112); r('#e5d9bc', x + 7, 52, 124, 98);
    r('#91bdc1', x + 12, 57, 114, 88); r('#bce0d8', x + 16, 61, 106, 80);
    r('#dcefe0', x + 22, 104, 94, 4); r('#e5d9bc', x + 65, 55, 7, 91); r('#e5d9bc', x + 10, 98, 118, 6);
    r('#725c49', x - 5, 151, 148, 8);
  }
  r('#80674f', 354, 42, 252, 120); r('#394f47', 362, 50, 236, 104);
  r('#6c8a76', 382, 69, 88, 5); r('#9ab19a', 382, 82, 130, 4); r('#6c8a76', 382, 95, 66, 4);
  r('#dfc69c', 530, 65, 42, 42); r('#c7a87b', 536, 74, 28, 3); r('#c7a87b', 536, 83, 22, 3);
  // Shelves, books and plants.
  for (const x of [246, 654]) {
    r('#75553e', x, 65, 60, 115); r('#b68c61', x + 6, 71, 48, 102);
    for (const y of [104, 144]) r('#75553e', x + 4, y, 52, 6);
    ['#c66f53', '#e1bd70', '#5c8b7d', '#e5d2a9'].forEach((c, i) => { r(c, x + 10 + i * 10, 80, 7, 24); r(c, x + 10 + i * 10, 119, 7, 25); });
  }
  for (const x of [38, 874]) {
    r('#765345', x + 10, 198, 34, 25); r('#b96e4f', x + 6, 192, 42, 10);
    r('#477657', x + 22, 154, 8, 40); r('#659469', x + 7, 158, 20, 17); r('#54845d', x + 26, 145, 19, 22); r('#79a676', x + 14, 145, 13, 14);
  }
  // Discussion rug and table.
  r('#987a65', 315, 328, 330, 123); r('#dfc8a6', 321, 334, 318, 111); r('#d1b391', 329, 342, 302, 95);
  r('#76503c', 389, 355, 182, 50); r('#ae7954', 382, 342, 196, 32); r('#dbac7c', 390, 342, 180, 9);
  r('#f1dfbd', 429, 348, 35, 13); r('#d4c09f', 434, 352, 24, 2); r('#e5e0c8', 507, 348, 20, 13); r('#a66552', 511, 350, 12, 8);
  // Desk legs and chairs behind the characters.
  for (const x of [105, 685]) {
    r('#775441', x + 20, 320, 13, 75); r('#775441', x + 141, 320, 13, 75);
    r('#925e40', x, 285, 180, 43); r('#d4a171', x, 277, 180, 17); r('#e4b786', x + 5, 277, 170, 5);
    r('#384c50', x + 59, 237, 62, 40); r('#83a9a4', x + 65, 243, 50, 27); r('#bdd6c8', x + 69, 248, 30, 3); r('#648e88', x + 69, 257, 38, 3);
    r('#384c50', x + 84, 277, 12, 5); r('#e4d8bf', x + 123, 268, 25, 9); r('#6d9277', x + 22, 266, 15, 11);
    r('#4d6260', x + 64, 341, 52, 35); r('#6c827b', x + 69, 337, 42, 27); r('#394e4a', x + 84, 371, 12, 32); r('#394e4a', x + 64, 399, 52, 6);
  }
  r('#38524f', 20, 477, 920, 11); r('#203633', 12, 488, 936, 12);
}

// Original Kepler character sprites, represented as pixels and cached by the
// adapted Pixel Agents sprite renderer. Frames differ only for observed work.
function characterPixels(role: Role, frame: number): string[][] {
  const pixels = Array.from({ length: 44 }, () => Array<string>(27).fill(''));
  const r = (c: string, x: number, y: number, w: number, h: number) => {
    for (let row = y; row < y + h; row++) for (let col = x; col < x + w; col++) pixels[row][col] = c;
  };
  const shirt = role === 'analyst' ? '#4d8290' : '#b66f5e';
  const hair = role === 'analyst' ? '#403d3b' : '#694a3a';
  r('#543d35', 5, 38, 7, 6); r('#543d35', 15, 38, 7, 6);
  r('#45525a', 5, 30, 7, 9); r('#45525a', 15, 30, 7, 9);
  r(shirt, 3, 18, 21, 15); r('#efd1ae', 0, 21, 4, 10); r('#efd1ae', 23, frame ? 19 : 21, 4, 10);
  r('#e9bf9b', 7, 14, 13, 7); r('#f2cba7', 4, 5, 17, 14); r(hair, 3, 2, 19, 6); r(hair, 3, 6, 4, 8);
  if (role === 'skeptic') r(hair, 19, 6, 4, 12);
  r('#473b37', 9, 11, 2, 2); r('#473b37', 16, 11, 2, 2); r('#b37d6c', 11, 15, 4, 1);
  r(role === 'analyst' ? '#8ab4b5' : '#e0a996', 8, 21, 10, 2);
  return pixels;
}
const characterSprites = {
  analyst: [characterPixels('analyst', 0), characterPixels('analyst', 1)],
  skeptic: [characterPixels('skeptic', 0), characterPixels('skeptic', 1)],
};
function drawCharacter(ctx: CanvasRenderingContext2D, box: Box, role: Role, frame: number, active: boolean) {
  ctx.drawImage(getCachedSprite(characterSprites[role][active ? frame : 0], 2), box.x + 13, box.y + 10);
}

function boxStyle(box: Box): React.CSSProperties {
  return { left: `${box.x / WIDTH * 100}%`, top: `${box.y / HEIGHT * 100}%`, width: `${box.width / WIDTH * 100}%`, height: `${box.height / HEIGHT * 100}%` };
}

export function ResearchOffice({ scene, onSelectAgent, onSelectMessage }: {
  scene: OfficeState;
  onSelectAgent: (role: Role) => void;
  onSelectMessage: (eventId: string) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const layout = officeLayout(scene);
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    let frame = 0, animation = 0, timer = 0, visible = typeof IntersectionObserver === 'undefined';
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sprites: Record<Role, HTMLImageElement> = { analyst: new Image(), skeptic: new Image() };
    sprites.analyst.src = '/research-office/char_0.png';
    sprites.skeptic.src = '/research-office/char_3.png';
    const isActive = (role: Role) => ['researching', 'tool'].includes(scene.agents[role].state);
    const animate = () => scene.connection === 'connected' && !document.hidden && visible && !media.matches && (isActive('analyst') || isActive('skeptic'));
    const draw = () => {
      ctx.imageSmoothingEnabled = false;
      drawOffice(ctx);
      (['analyst', 'skeptic'] as const).forEach(role => {
        const sprite = sprites[role];
        const box = layout[role].character;
        if (sprite.complete && sprite.naturalWidth === 112 && sprite.naturalHeight === 96) {
          const working = scene.connection === 'connected' && isActive(role) && !media.matches;
          const state = scene.agents[role].state;
          const sourceX = working && state === 'tool' ? 48 + frame * 16 : working && state === 'researching' ? 80 + frame * 16 : 16;
          ctx.drawImage(sprite, sourceX, 0, 16, 32, box.x + 13, box.y + 2, 48, 96);
        } else drawCharacter(ctx, box, role, frame, scene.connection === 'connected' && isActive(role));
      });
    };
    const tick = () => {
      animation = 0;
      if (!animate()) return;
      frame = frame ? 0 : 1; draw();
      timer = window.setTimeout(() => { animation = requestAnimationFrame(tick); }, 166);
    };
    const sync = () => {
      if (animation) cancelAnimationFrame(animation);
      window.clearTimeout(timer);
      animation = 0; frame = 0;
      if (!document.hidden && visible) draw();
      if (animate()) timer = window.setTimeout(() => { animation = requestAnimationFrame(tick); }, 166);
    };
    sprites.analyst.onload = sync; sprites.skeptic.onload = sync;
    const observer = typeof IntersectionObserver === 'undefined' ? null : new IntersectionObserver(entries => { visible = entries[0]?.isIntersecting ?? false; sync(); });
    observer?.observe(canvas);
    document.addEventListener('visibilitychange', sync); media.addEventListener('change', sync); sync();
    return () => { if (animation) cancelAnimationFrame(animation); window.clearTimeout(timer); sprites.analyst.onload = null; sprites.skeptic.onload = null; observer?.disconnect(); document.removeEventListener('visibilitychange', sync); media.removeEventListener('change', sync); };
  }, [scene.connection, scene.agents.analyst.state, scene.agents.skeptic.state]);
  return <section className="research-office" aria-label="Research office">
    <style>{styles}</style>
    <div className="research-office__canvas-wrap">
      <canvas ref={canvasRef} width={WIDTH} height={HEIGHT} aria-hidden="true" />
      {(['analyst', 'skeptic'] as const).map(role => {
        const agent = scene.agents[role];
        const message = agent.messages[agent.messages.length - 1];
        const model = agent.model;
        return <React.Fragment key={role}>
          <button type="button" className="research-office__agent" style={boxStyle(layout[role].character)} onClick={() => onSelectAgent(role)} aria-label={`Open ${role} details, ${agent.state}${model ? `, ${model.model}: ${model.status}` : ''}`}>
            <span className="research-office__agent-label">{role}<small>{agent.state}</small></span>
          </button>
          {message && <button type="button" className="research-office__bubble" style={boxStyle(layout[role].bubble)} onClick={() => onSelectMessage(message.eventId)} aria-label={`Open ${role} message: ${message.text}`}><strong>{role}{message.recipient && ` → ${message.recipient}`}</strong><span>{message.text}</span></button>}
        </React.Fragment>;
      })}
    </div>
    <div className="research-office__health" aria-label="Configured agent health">
      {(['analyst', 'skeptic'] as const).map(role => <span key={role}><strong>{role}</strong> · {scene.agents[role].model ? `${scene.agents[role].model!.model}: ${scene.agents[role].model!.status}` : 'model health unknown'}</span>)}
      {!scene.roomId && <span>No room selected</span>}
    </div>
    <div className="research-office__mobile" aria-label="Office participants">
      {(['analyst', 'skeptic'] as const).map(role => {
        const agent = scene.agents[role]; const message = agent.messages[agent.messages.length - 1];
        return <div key={role}><button type="button" onClick={() => onSelectAgent(role)}>{role} · {agent.state}{agent.model ? ` · ${agent.model.model}: ${agent.model.status}` : ''}</button>{message && <button type="button" onClick={() => onSelectMessage(message.eventId)}>{role}{message.recipient && ` → ${message.recipient}`} · Message: {message.text}</button>}</div>;
      })}
    </div>
  </section>;
}

const styles = `
.research-office { width: 100%; }
.research-office__canvas-wrap { position: relative; width: 100%; aspect-ratio: 960 / 500; overflow: hidden; background: #243b3b; border: 5px solid #273d3a; border-radius: 8px; box-shadow: 0 12px 30px #1b302a26; }
.research-office canvas { display: block; width: 100%; height: 100%; image-rendering: pixelated; }
.research-office__agent, .research-office__bubble { position: absolute; cursor: pointer; font-family: inherit; }
.research-office__agent { background: transparent; border: 0; padding: 0; }
.research-office__agent:focus-visible, .research-office__bubble:focus-visible { outline: 3px solid #fef4b2; outline-offset: 2px; }
.research-office__agent-label { position: absolute; top: 100%; left: 50%; transform: translateX(-50%); background: #263d39; color: #fff8e8; padding: 3px 8px; border-radius: 4px; font-size: clamp(9px, 1.1vw, 13px); line-height: 1.2; text-transform: capitalize; white-space: nowrap; }
.research-office__agent-label small { display: block; color: #c6d9ca; font-size: .8em; }
.research-office__bubble { background: #fff8e9; color: #2a403d; border: 3px solid #455b50; border-radius: 5px; box-shadow: 3px 3px 0 #6a7a69; text-align: left; padding: 5px 7px; font-size: clamp(9px, 1.15vw, 13px); line-height: 1.25; overflow: hidden; }
.research-office__bubble strong { display: block; text-transform: capitalize; font-size: .85em; margin-bottom: 2px; }
.research-office__bubble span { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.research-office__health { display: flex; flex-wrap: wrap; gap: 6px 16px; padding: 8px 2px; color: #536b5f; font-size: 12px; }
.research-office__health strong { text-transform: capitalize; }
.research-office__mobile { display: none; }
@media (max-width: 600px) { .research-office__canvas-wrap .research-office__agent, .research-office__canvas-wrap .research-office__bubble { display: none; } .research-office__mobile { display: grid; gap: 8px; margin-top: 8px; } .research-office__mobile div { display: flex; flex-wrap: wrap; gap: 6px; } .research-office__mobile button { border: 1px solid #879c90; border-radius: 5px; padding: 6px 9px; background: #f5f1e6; color: #253c36; text-align: left; overflow-wrap: anywhere; } }
`;
