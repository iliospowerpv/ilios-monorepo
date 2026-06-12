import React, { useEffect, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';

interface ParsingProgressIndicatorProps {
  status: string;
  startTime?: string | null;
}

function formatElapsed(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

const ParsingProgressIndicator: React.FC<ParsingProgressIndicatorProps> = ({ status, startTime }) => {
  const normalized = status.toLowerCase().replace(/\s+/g, '_');
  const isQueued = normalized === 'queued';

  const mountRef = useRef<number>(Date.now());
  const [now, setNow] = useState<number>(Date.now());

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  const parsedStart = startTime ? new Date(startTime).getTime() : NaN;
  const baseTime = Number.isFinite(parsedStart) ? parsedStart : mountRef.current;
  const elapsedSeconds = (now - baseTime) / 1000;

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'primary.light',
        borderRadius: 1,
        bgcolor: 'action.hover',
        p: 2,
        mb: 2
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1 }}>
        <Typography variant="body2" role="status" aria-live="polite" sx={{ fontWeight: 600, color: 'primary.main' }}>
          {isQueued ? 'Queued — waiting to start…' : 'AI parsing in progress…'}
        </Typography>
        <Typography
          aria-hidden="true"
          variant="body2"
          sx={{ fontVariantNumeric: 'tabular-nums', color: 'text.secondary', whiteSpace: 'nowrap' }}
        >
          {formatElapsed(elapsedSeconds)} elapsed
        </Typography>
      </Box>
      <LinearProgress color="primary" sx={{ borderRadius: 1, height: 6 }} />
      <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
        AI is reading this document. Large files (like PVsyst reports) can take a few minutes. This panel refreshes
        automatically every few seconds — you can keep working and come back.
      </Typography>
    </Box>
  );
};

export default ParsingProgressIndicator;
