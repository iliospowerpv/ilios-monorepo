import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TaskDetails from '../../../../../components/forms/TaskDetails/TaskDetails';
import TaskDescription from './components/TaskDescription';
import TaskComments from '../../../../../components/forms/TaskComments/TaskComments';
import { siteBoardsQuery, taskDetailsQuery, siteCrumbsQuery, summaryDetailsQuery } from './loader';
import DocumentList from '../../../../../components/common/DocumentList/DocumentList';
import SummaryOfEvents from '../../../../../components/forms/SummaryOfEvents/SummaryOfEvents';
import { Button } from '@mui/material';
import { ApiClient } from '../../../../../api';
import { useNotify } from '../../../../../contexts/notifications/notifications';
import SummaryForm from '../../../../../components/forms/SummaryForm/SummaryForm';
import SiteConditions from '../../../../../components/common/SiteConditions/SiteConditions';
import FieldDiscovery from '../../../../../components/common/FieldDiscovery/FieldDiscovery';

export const SiteTaskPage: React.FC = () => {
  const { taskId, siteId } = useParams();
  const notify = useNotify();
  const queryClient = useQueryClient();
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
    siteCrumbsQuery(Number.parseInt(siteId), true)
  );

  const { data: siteBoards, isLoading: isLoadingSiteBoards } = useQuery(
    siteBoardsQuery(Number.parseInt(siteId), true, true)
  );

  const [board] = siteBoards ? siteBoards.items : [];

  const { data: taskDetails, isLoading: isLoadingTaskDetails } = useQuery(
    taskDetailsQuery(board ? board.id : -1, Number.parseInt(taskId), !!board, true)
  );

  const { data: summaryDetails } = useQuery(
    summaryDetailsQuery(board ? board.id : -1, taskId, taskDetails?.site_visit_added, true)
  );

  const { mutateAsync: createSiteVisit } = useMutation({
    mutationFn: () => ApiClient.taskManagement.createSiteVisit(board ? board.id : -1, taskId)
  });

  const createSite = async () => {
    try {
      await createSiteVisit();
      queryClient.removeQueries({ queryKey: ['tasks', 'details'] });
      notify('Site visit details was successfully created!');
    } catch (e: any) {
      notify('Site visit details failed. Please try again');
    }
  };

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
      <Typography variant="h4" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {`${taskData.external_id}: ${taskData.name}`}
      </Typography>
      <Box display="flex" flexDirection="row" justifyContent="flex-end">
        <Button
          variant="contained"
          color="primary"
          data-testid="actions__add-btn"
          onClick={() => {
            createSite();
          }}
          disabled={isLoadingTaskDetails || taskData?.site_visit_added}
        >
          Site Visit
        </Button>
      </Box>
      <Box paddingTop={1}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Box>
              <TaskDetails
                scope="site"
                taskData={taskData}
                initialMode={editOnLanding ? 'edit' : 'view'}
                siteId={siteDetails.id}
                siteName={siteDetails.name}
                boardId={board.id}
                module="O&M"
              />
            </Box>
            <Box>
              {taskData?.site_visit_added && summaryDetails ? (
                <SummaryForm
                  scope="site"
                  taskData={summaryDetails}
                  taskId={taskData?.id}
                  siteName={siteDetails.name}
                  boardId={board.id}
                />
              ) : null}
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
              {taskData?.site_visit_added && <SiteConditions boardId={board.id} taskId={taskData.id} />}
              {taskData?.site_visit_added && <FieldDiscovery boardId={board.id} taskId={taskData.id} />}
            </Box>
            <TaskComments taskId={taskData.id} boardId={board.id} module="O%26M%20%28Production%20Monitoring%29" />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default SiteTaskPage;
