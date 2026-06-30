import * as React from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import LinearProgress from '@mui/material/LinearProgress';
import Divider from '@mui/material/Divider';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

import { ApiClient } from '../../../api';

const USAGE_KEY = ['assistant', 'admin', 'usage'];

const StatCard: React.FC<{ label: string; value: number | string }> = ({ label, value }) => (
  <Paper variant="outlined" sx={{ p: 2 }}>
    <Typography variant="h5" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
      {value}
    </Typography>
    <Typography variant="caption" color="text.secondary">
      {label}
    </Typography>
  </Paper>
);

// Admin-only, read-only observability over the ISOLATED assistant tables. The backend gate is the
// source of truth (403 for non-admins, 404 when the flag is off); this panel just renders the
// aggregate or a friendly fallback. It never reads business/operational data.
export const AssistantUsagePanel: React.FC = () => {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: USAGE_KEY,
    queryFn: ApiClient.assistant.getAdminUsage,
    retry: false,
    staleTime: 60 * 1000
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (isError || !data) {
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    if (status === 404) {
      return <Alert severity="info">The AI Assistant is not enabled, so there is no usage to report.</Alert>;
    }
    if (status === 403) {
      return <Alert severity="warning">You don&apos;t have permission to view AI Assistant usage.</Alert>;
    }
    return <Alert severity="error">Unable to load AI Assistant usage right now.</Alert>;
  }

  const maxToolCount = data.top_tools.reduce((max, tool) => Math.max(max, tool.count), 0);
  // Additive UI-interaction analytics (Task #89). Defensive against an older cached payload that
  // predates the `interactions` field.
  const interactions = data.interactions;
  const maxCardClick = interactions
    ? interactions.action_card_clicks.reduce((max, card) => Math.max(max, card.count), 0)
    : 0;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
          Conversations
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)' }, gap: 1.5 }}>
          <StatCard label="Total" value={data.conversations_total} />
          <StatCard label="Active" value={data.conversations_active} />
          <StatCard label="Archived" value={data.conversations_archived} />
        </Box>
      </Box>

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
          Messages
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, 1fr)' }, gap: 1.5 }}>
          <StatCard label="Total" value={data.messages_total} />
          <StatCard label="From users" value={data.user_messages} />
          <StatCard label="From assistant" value={data.assistant_messages} />
          <StatCard label="Distinct users" value={data.distinct_users} />
        </Box>
      </Box>

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
          Feedback
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)' }, gap: 1.5 }}>
          <StatCard label="Helpful" value={data.feedback_up} />
          <StatCard label="Not helpful" value={data.feedback_down} />
          <StatCard label="No rating" value={data.feedback_none} />
        </Box>
      </Box>

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
          Top read-only tools
        </Typography>
        {data.top_tools.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No tool usage recorded yet.
          </Typography>
        ) : (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack spacing={1.5} divider={<Divider flexItem />}>
              {data.top_tools.map(tool => (
                <Box key={tool.name}>
                  <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {tool.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {tool.count}
                    </Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={maxToolCount > 0 ? Math.round((tool.count / maxToolCount) * 100) : 0}
                    color="secondary"
                  />
                </Box>
              ))}
            </Stack>
          </Paper>
        )}
      </Box>

      {interactions ? (
        <>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
              Native adoption
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, 1fr)' }, gap: 1.5 }}>
              <StatCard label="Opens" value={interactions.opens} />
              <StatCard label="Dismissals" value={interactions.dismissals} />
              <StatCard label="Prompts sent" value={interactions.prompt_submissions} />
              <StatCard label="In-wizard prompts" value={interactions.companion_prompt_submissions} />
              <StatCard label="Suggested-prompt picks" value={interactions.suggested_prompt_clicks} />
              <StatCard label="Sources opened" value={interactions.sources_disclosures_opened} />
              <StatCard label="Discoverability clicks" value={interactions.discoverability_entry_clicks} />
              <StatCard label="Total events" value={interactions.events_total} />
            </Box>
          </Box>

          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
              Guidance &amp; hints
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)' }, gap: 1.5 }}>
              <StatCard label="First-run shown" value={interactions.first_run_shown} />
              <StatCard label="First-run opened" value={interactions.first_run_opened} />
              <StatCard label="First-run dismissed" value={interactions.first_run_dismissed} />
              <StatCard label="Hints shown" value={interactions.proactive_hint_shown} />
              <StatCard label="Hints opened" value={interactions.proactive_hint_opened} />
              <StatCard label="Hints dismissed" value={interactions.proactive_hint_dismissed} />
            </Box>
          </Box>

          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
              Action cards clicked
            </Typography>
            {interactions.action_card_clicks.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No action-card clicks recorded yet.
              </Typography>
            ) : (
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Stack spacing={1.5} divider={<Divider flexItem />}>
                  {interactions.action_card_clicks.map(card => (
                    <Box key={card.kind}>
                      <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {card.kind}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {card.count}
                        </Typography>
                      </Stack>
                      <LinearProgress
                        variant="determinate"
                        value={maxCardClick > 0 ? Math.round((card.count / maxCardClick) * 100) : 0}
                        color="secondary"
                      />
                    </Box>
                  ))}
                </Stack>
              </Paper>
            )}
          </Box>
        </>
      ) : null}
    </Stack>
  );
};

export default AssistantUsagePanel;
