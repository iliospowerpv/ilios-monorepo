import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TaskDetails from '../../../../components/forms/TaskDetails/TaskDetails';
import TaskDescription from '../../../../components/forms/TaskDescription/TaskDescription';
import TaskComments from '../../../../components/forms/TaskComments/TaskComments';
import { siteBoardsQuery, taskDetailsQuery, siteDetailsQuery } from './loader';
import DocumentList from '../../../../components/common/DocumentList/DocumentList';
import SummaryOfEvents from '../../../../components/forms/SummaryOfEvents/SummaryOfEvents';

export const SiteTaskPage: React.FC = () => {
  const { taskId, siteId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [editOnLanding] = React.useState(
    searchParams.has('editOnLanding') && searchParams.get('editOnLanding') === 'true'
  );

  if (!siteId || !Number.isSafeInteger(Number.parseInt(siteId))) {
    throw new Error(`Provided site id "${siteId}" is invalid.`);
  }

  if (!taskId || !Number.isSafeInteger(Number.parseInt(taskId))) {
    throw new Error(`Provided task id "${taskId}" is invalid.`);
  }

  React.useEffect(() => {
    if (searchParams.has('editOnLanding')) {
      const token = searchParams.get('editOnLanding');
      if (token) {
        searchParams.delete('editOnLanding');
        setSearchParams(searchParams, { replace: true });
      }
    }
  }, [searchParams, setSearchParams]);

  const { data: siteDetails, isLoading: isLoadingSiteDetails } = useQuery(
    siteDetailsQuery(Number.parseInt(siteId), true, true)
  );

  const { data: siteBoards, isLoading: isLoadingSiteBoards } = useQuery(
    siteBoardsQuery(Number.parseInt(siteId), true, true)
  );

  const [board] = siteBoards ? siteBoards.items : [];

  const { data: taskDetails, isLoading: isLoadingTaskDetails } = useQuery(
    taskDetailsQuery(board ? board.id : -1, Number.parseInt(taskId), !!board, true)
  );

  if (
    isLoadingSiteBoards ||
    isLoadingTaskDetails ||
    isLoadingSiteDetails ||
    !siteBoards ||
    !taskDetails ||
    !siteDetails
  )
    return null;

  const { description, ...taskData } = taskDetails;

  return (
    <Box maxWidth="1600px" mx="auto">
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {`${taskData.external_id}: ${taskData.name}`}
      </Typography>
      <Box paddingTop={1}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Box mb="18px">
              <TaskDetails
                scope="site"
                taskData={taskData}
                initialMode={editOnLanding ? 'edit' : 'view'}
                siteId={siteDetails.id}
                siteName={siteDetails.name}
                boardId={board.id}
              />
            </Box>
          </Grid>
          <Grid item xs={12} md={8}>
            <Box mb="18px">
              <TaskDescription descriptionText={description} boardId={board.id} taskId={taskData.id} />
            </Box>
            <Box mb="18px">
              <SummaryOfEvents
                descriptionText={taskDetails?.summary_of_events}
                boardId={board.id}
                taskId={taskData.id}
              />
            </Box>
            <Box mb="18px">
              <DocumentList boardId={board.id} taskId={taskData.id} />
            </Box>
            <TaskComments taskId={taskData.id} boardId={board.id} />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default SiteTaskPage;
