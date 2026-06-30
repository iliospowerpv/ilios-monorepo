import { useCallback, useEffect, useState } from 'react';

// Client-side persistence for the floating AI Assistant launcher position. The launcher snaps to the
// nearest left/right screen edge (never the page center) and keeps a vertical offset, so it stays out
// of the way of key controls while honoring the user's preferred spot. Stored per browser only.
const STORAGE_KEY = 'ilios_assistant_launcher_position';
export const LAUNCHER_MARGIN = 24;
// Approximate launcher footprint used only for safe clamping math; exact size is driven by MUI.
const LAUNCHER_HEIGHT = 56;

export type LauncherSide = 'left' | 'right';

export interface LauncherPosition {
  side: LauncherSide;
  // Top coordinate (px) of the launcher within the viewport.
  y: number;
}

const getViewportHeight = (): number => (typeof window !== 'undefined' ? window.innerHeight : 800);

// Keep the launcher fully on-screen with a comfortable margin even as the viewport changes.
const clampY = (y: number, viewportHeight: number): number => {
  const max = Math.max(LAUNCHER_MARGIN, viewportHeight - LAUNCHER_HEIGHT - LAUNCHER_MARGIN);
  return Math.min(Math.max(y, LAUNCHER_MARGIN), max);
};

// Default mirrors the historical placement: anchored to the bottom-right corner.
const getDefaultPosition = (): LauncherPosition => {
  const viewportHeight = getViewportHeight();
  return { side: 'right', y: clampY(viewportHeight - LAUNCHER_HEIGHT - LAUNCHER_MARGIN, viewportHeight) };
};

const isValidPosition = (value: unknown): value is LauncherPosition => {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Record<string, unknown>;
  return (
    (candidate.side === 'left' || candidate.side === 'right') &&
    typeof candidate.y === 'number' &&
    Number.isFinite(candidate.y)
  );
};

// Read the stored preference, falling back to the default on missing/malformed/stale (off-screen) data.
const readStoredPosition = (): LauncherPosition => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (isValidPosition(parsed)) {
        return { side: parsed.side, y: clampY(parsed.y, getViewportHeight()) };
      }
    }
  } catch {
    // Ignore malformed/unavailable localStorage.
  }
  return getDefaultPosition();
};

export const useAssistantLauncherPosition = () => {
  const [position, setPositionState] = useState<LauncherPosition>(readStoredPosition);

  const setPosition = useCallback((next: LauncherPosition) => {
    const safe: LauncherPosition = { side: next.side, y: clampY(next.y, getViewportHeight()) };
    setPositionState(safe);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(safe));
    } catch {
      // Ignore localStorage write failures (e.g. private mode / quota).
    }
  }, []);

  // Re-clamp the vertical offset when the viewport shrinks so the launcher never drifts off-screen.
  useEffect(() => {
    const handleResize = () => {
      setPositionState(prev => {
        const clamped = clampY(prev.y, window.innerHeight);
        return clamped === prev.y ? prev : { ...prev, y: clamped };
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return { position, setPosition };
};
