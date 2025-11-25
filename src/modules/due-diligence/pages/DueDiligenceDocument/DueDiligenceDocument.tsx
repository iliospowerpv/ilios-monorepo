import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import DocumentDetails from './components/DocumentDetails';
import DocumentDescription from './components/DocumentDescription';
import DocumentComments from './components/DocumentComments';
import { documentInfoQuery } from './loader';
import DocumentList from './components/DocumentList';
import TaskDetails from '../../../../components/forms/TaskDetails/TaskDetails';

export const DueDiligenceDocumentPage: React.FC = () => {
  const { documentId, siteId } = useParams();

  if (!siteId || !Number.isSafeInteger(Number.parseInt(siteId))) {
    throw new Error(`Provided site id "${siteId}" is invalid.`);
  }

  if (!documentId || !Number.isSafeInteger(Number.parseInt(documentId))) {
    throw new Error(`Provided document id "${documentId}" is invalid.`);
  }

  const { data: documentInfo, isLoading: isLoadingDocumentInfo } = useQuery(
    documentInfoQuery(Number.parseInt(siteId), Number.parseInt(documentId), true, true)
  );

  if (isLoadingDocumentInfo || !documentInfo) return null;
  const { description, name, site, id, task, display_working_zone } = documentInfo;

  return (
    <Box maxWidth="1600px" mx="auto">
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {name}
      </Typography>
      <Box paddingTop={1}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Box>
              <DocumentDetails siteId={site.id} documentId={id} boardId={task.board_id} documentInfo={documentInfo} />
            </Box>
            <Box>
              <TaskDetails scope="diligence" taskData={task} boardId={task.board_id} />
            </Box>
            <Box>
              <DocumentDescription siteId={site.id} documentId={id} descriptionText={description} />
            </Box>
          </Grid>
          <Grid item xs={12} md={8}>
            <DocumentList
              siteId={site.id}
              documentId={id}
              boardId={documentInfo.task.board_id}
              documentKind={display_working_zone}
              taskId={task?.id}
            />
            <DocumentComments
              documentId={documentInfo.id}
              boardId={documentInfo.task.board_id}
              taskId={documentInfo.task.id}
            />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default DueDiligenceDocumentPage;
