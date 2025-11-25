import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import Zoom from '@mui/material/Zoom';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Fade from '@mui/material/Fade';
import Avatar from '@mui/material/Avatar';
import PlaceIcon from '@mui/icons-material/Place';
import PersonIcon from '@mui/icons-material/Person';

import { useNotify } from '../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../api';

import AssigneeSearchField from '../../../../../components/forms/AssigneeSearchField/AssigneeSearchField';
import { FieldCell, TextBox, DetailsContainer } from './DocumentDetails.styles';

type UpdateDocumentDetailsFunc = typeof ApiClient.dueDiligence.updateDocumentDetails;
type UpdatedDocumentAttributes = Parameters<UpdateDocumentDetailsFunc>[number]['attributes'];

interface Approver {
  id: number;
  first_name: string;
  last_name: string;
}

interface SiteInfo {
  id: number;
  name: string;
  address: string;
}

interface SectionInfo {
  id: number;
  name: string;
}

interface DocumentInfo {
  type: string | null;
  site: SiteInfo;
  section: SectionInfo;
  approver: Approver | null;
  task: {
    id: number;
  };
}
interface DocumentDetailsProps {
  siteId: number;
  documentId: number;
  boardId: number;
  documentInfo: DocumentInfo;
}

interface DocumentDetailsFormFields {
  approver: Approver | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

export const DocumentDetails: React.FC<DocumentDetailsProps> = ({ siteId, documentId, boardId, documentInfo }) => {
  const [mode, setMode] = React.useState<'view' | 'edit'>('view');

  const queryClient = useQueryClient();
  const notify = useNotify();

  const { mutateAsync: updateDocumentDetails } = useMutation({
    mutationFn: (attributes: UpdatedDocumentAttributes) =>
      ApiClient.dueDiligence.updateDocumentDetails({ siteId, documentId, attributes })
  });

  const { handleSubmit, formState, control, reset } = useForm<DocumentDetailsFormFields>({
    mode: 'all',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      approver: documentInfo.approver
    }
  });

  const { isValid, isSubmitting, isDirty } = formState;

  React.useEffect(() => {
    reset({
      approver: documentInfo.approver
    });
  }, [documentInfo, reset]);

  const onSubmit: SubmitHandler<DocumentDetailsFormFields> = async data => {
    try {
      const response = await updateDocumentDetails({
        approver_id: data.approver ? data.approver.id : null
      });
      notify(response.message || `Document details were successfully updated.`);
      reset({
        approver: data.approver
      });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      mode === 'edit' && setMode('view');
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when updating the document details...');
    }
  };

  const handleClickEdit = () => setMode('edit');

  const handleClickCancel = () => {
    reset();
    setMode('view');
  };

  const { approver, type, site, section } = documentInfo;

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
        Details
      </Typography>
      <DetailsContainer position="relative" display="flex" flexDirection="column" flexGrow={1}>
        <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
          <TableBody>
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }} component="th" scope="row" width="120px">
                <TextBox fieldName>Approver</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                {mode === 'view' ? (
                  <Box display="inline-flex" alignItems="center">
                    <Avatar
                      sx={{
                        width: '25px',
                        height: '25px',
                        fontSize: '12px',
                        fontWeight: '600',
                        backgroundColor: theme => theme.color.blueGray,
                        lineHeight: '25px',
                        display: 'inline-flex',
                        mr: '6px'
                      }}
                    >
                      {approver ? (
                        `${approver.first_name.charAt(0)}${approver.last_name.charAt(0)}`
                      ) : (
                        <PersonIcon fontSize="small" />
                      )}
                    </Avatar>
                    <TextBox>{approver ? `${approver.first_name} ${approver.last_name}` : 'None'}</TextBox>
                  </Box>
                ) : (
                  <Controller
                    name="approver"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <AssigneeSearchField
                        {...field}
                        boardId={boardId}
                        value={value}
                        onChange={(evt, value) => onChange(value)}
                        ref={ref}
                        inputStyleOverrides={inputStyles}
                        placeholder="Add"
                        taskId={documentInfo?.task?.id}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="100px">
                <TextBox fieldName>Type</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                <TextBox>{type}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="100px">
                <TextBox fieldName>Site</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                <Box display="inline-flex" alignItems="center">
                  <PlaceIcon fontSize="small" sx={{ mr: '4px', color: '#707070' }} />
                  <TextBox>{site.name}</TextBox>
                </Box>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="100px">
                <TextBox fieldName>Section</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                <TextBox>{section.name}</TextBox>
              </FieldCell>
            </TableRow>
          </TableBody>
        </Table>
        <Zoom in={mode === 'view'}>
          <Box position="absolute" top="8px" right="8px" borderRadius="50%" bgcolor="rgba(255, 255, 255, 0.85)">
            <IconButton data-testid="document_details-details-edit_btn" size="medium" onClick={handleClickEdit}>
              <EditIcon />
            </IconButton>
          </Box>
        </Zoom>
      </DetailsContainer>
      <Fade in={mode === 'edit'} timeout={{ enter: 1000, exit: 1000 }}>
        <Stack direction="row" width="100%" py="10px" spacing={1} justifyContent="flex-end">
          <Button disabled={!isValid || !isDirty || isSubmitting} variant="contained" size="small" type="submit">
            Save
          </Button>
          <Button disabled={isSubmitting} variant="outlined" size="small" onClick={handleClickCancel}>
            Cancel
          </Button>
        </Stack>
      </Fade>
    </Box>
  );
};

export default DocumentDetails;
