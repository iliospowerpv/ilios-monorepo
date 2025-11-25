import React, { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import DocViewer, { DocViewerRenderers } from '@cyntler/react-doc-viewer';
import { AxiosError } from 'axios';
import Box from '@mui/material/Box';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import Backdrop from '@mui/material/Backdrop';
import CircularProgress from '@mui/material/CircularProgress';
import Fade from '@mui/material/Fade';
import { ApiClient, FileItem } from '../../../../../api';
import {
  SubHeader,
  DocumentPreviewContainer,
  TermName,
  AIResponseContainer,
  AccordionStyled,
  AccordionSummaryStyled,
  DialogTitleStyled,
  DialogContentStyled,
  AIText,
  DocunentPreviewModal,
  DocunentPreviewModalContent,
  DocunentPreviewModalViewbox
} from './DocumentModal.styles';
import DocumentTermUserInputField, { DocumentTermUserInputFieldRef } from './DocumentTermUserInputField';
import DocumentPoisonPill from './DocumentPoisonPill';
import { BootstrapTooltip } from '../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNotify } from '../../../../../contexts/notifications/notifications';
import DocumentModalComments from './DocumentModalComments';

dayjs.extend(utc);

interface DocumentModal {
  open: boolean;
  fileUrl: string;
  file: FileItem | null;
  documentId: number;
  siteId: number;
  boardId: number;
  onClose: () => void;
  taskId: number;
}

interface Comment {
  id: number;
  entity_id: number;
  text: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
}

interface CollapsibleDocumentTermRenderer {
  id: number | null;
  termName: string;
  aiValue: string | null;
  userValue: string | null;
  documentId: number;
  siteId: number;
  isPoisonPill: boolean;
  poisonPillDetails: string | null;
  legal_term: string | null;
  comments: Comment[] | null;
  boardId: number;
  fileId: number;
  taskId: number;
}

const CollapsibleDocumentTermRenderer: React.FC<CollapsibleDocumentTermRenderer> = props => {
  const {
    id,
    termName,
    aiValue,
    userValue,
    documentId,
    siteId,
    isPoisonPill,
    poisonPillDetails,
    legal_term,
    comments,
    boardId,
    fileId,
    taskId
  } = props;
  const userInputFormRef = React.useRef<DocumentTermUserInputFieldRef | null>(null);
  const [expanded, setExpanded] = React.useState<boolean>(true);

  const copyToTextField = (text: string | null) => {
    if (!text) return;
    const textToPopulate = text.length > 2000 ? text.substring(0, 2000) : text;
    userInputFormRef.current?.setValue && userInputFormRef.current?.setValue(textToPopulate);
  };

  return (
    <AccordionStyled expanded={expanded} onChange={() => setExpanded(prevExpanded => !prevExpanded)}>
      <AccordionSummaryStyled expandIcon={<ExpandMoreIcon />}>
        <TermName>{termName}</TermName>
      </AccordionSummaryStyled>
      <AccordionDetails sx={{ display: 'flex', padding: '8px 0 16px 16px' }}>
        <Box flex="1">
          <AIResponseContainer>
            <Typography variant="h6" fontSize="16px" fontWeight="600" py="8px">
              Legal Terms
            </Typography>
            <AIText bgColor>{legal_term}</AIText>
            <Typography variant="h6" fontSize="16px" fontWeight="600" py="8px">
              Value
              <BootstrapTooltip title="Copy" placement="top">
                <IconButton
                  sx={{ position: 'absolute', right: '-30px', marginTop: '25px !important', padding: '8px', margin: 0 }}
                  onClick={() => copyToTextField(aiValue)}
                >
                  <ContentCopyIcon sx={{ fontSize: '20px', color: theme => theme.palette.text.secondary }} />
                </IconButton>
              </BootstrapTooltip>
            </Typography>
            <AIText>{aiValue}</AIText>
            <DocumentPoisonPill isPoisonPill={isPoisonPill} title={isPoisonPill ? poisonPillDetails : ''} />
          </AIResponseContainer>
          <DocumentTermUserInputField
            ref={userInputFormRef}
            documentId={documentId}
            siteId={siteId}
            termKey={termName}
            text={userValue}
          />
          <DocumentModalComments
            termId={id}
            termKey={termName}
            documentId={documentId}
            siteId={siteId}
            comments={comments}
            boardId={boardId}
            fileId={fileId}
            taskId={taskId}
          />
        </Box>
        <Box sx={{ padding: '4px', width: '36px' }}></Box>
      </AccordionDetails>
    </AccordionStyled>
  );
};

const DocumentModal: React.FC<DocumentModal> = props => {
  const { open, file, fileUrl, onClose, documentId, siteId, boardId, taskId } = props;
  const fileId = file?.id ?? -1;
  const [isProcessing, setIsProcessing] = useState(false);
  const queryClient = useQueryClient();
  const notify = useNotify();

  const {
    data: fileTermKeysData,
    isLoading: isLoadingFileTermKeysData,
    error: fileTermKeysDataLoadingError
  } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getFileParsingResult({ siteId, documentId, fileId }),
    queryKey: ['document-terms', { siteId, documentId, fileId }],
    enabled: open && fileId !== -1,
    retry: 1
  });

  const { mutateAsync: startParsing } = useMutation({
    mutationFn: (id: number) => ApiClient.dueDiligence.documentStartParsing(id, siteId, documentId),
    onSuccess: () => {
      notify(`This will take 10-15 minutes. Feel free to tackle another task and check back shortly!`);
      setIsProcessing(true);
    },
    onError: () => {
      notify('Something went wrong, try again later.');
    }
  });

  const { data: documentStatus } = useQuery({
    queryFn: async () => {
      return ApiClient.dueDiligence.documentParsingStatus(fileId, siteId, documentId);
    },
    queryKey: ['document-status', { siteId, documentId }],
    enabled: open && fileId !== -1,
    refetchInterval: !isProcessing ? isProcessing : 60000 // 1 min refetch interval
  });

  const handleStartParsing = async (fileId: number) => {
    try {
      await startParsing(fileId);
    } catch (e) {
      console.log(e);
    }
  };

  useEffect(() => {
    setIsProcessing(false);

    if (documentStatus?.status === 'Processing Failed') {
      notify('Processing failed');
      setIsProcessing(false);
    } else if (documentStatus?.status === 'Completed') {
      notify('Processing completed');
      setIsProcessing(false);
      queryClient.invalidateQueries({ queryKey: ['document-terms'] });
    } else if (documentStatus?.status === 'Processing') {
      setIsProcessing(true);
    } else if (documentStatus?.status === 'Not Started') {
      setIsProcessing(false);
    }

    return () => setIsProcessing(false);
  }, [documentStatus, file, notify]);

  React.useEffect(() => {
    if (fileTermKeysDataLoadingError) {
      notify(
        fileTermKeysDataLoadingError instanceof AxiosError
          ? fileTermKeysDataLoadingError.response?.data?.message || fileTermKeysDataLoadingError.message
          : fileTermKeysDataLoadingError.message
      );
    }
  }, [notify, fileTermKeysDataLoadingError]);

  const FileRenderer = React.useMemo(
    () =>
      file && fileUrl ? (
        <DocViewer
          pluginRenderers={DocViewerRenderers}
          documents={[{ uri: fileUrl }]}
          style={{ width: '100%', height: '100%' }}
          config={{
            header: {
              disableHeader: true,
              disableFileName: true
            },
            pdfVerticalScrollByDefault: true
          }}
        />
      ) : null,
    [file, fileUrl]
  );

  if (!file || !fileUrl) return null;

  return (
    <DocunentPreviewModal
      className="DocumentPreviewModal-root"
      onClose={onClose}
      aria-labelledby="customized-dialog-title"
      open={open}
      disableEnforceFocus
      disableAutoFocus
      disableRestoreFocus
    >
      <Fade in={open}>
        <DocunentPreviewModalViewbox className="DocumentPreviewModal-viewbox">
          <DocunentPreviewModalContent className="DocumentPreviewModal-content">
            <DialogTitleStyled id="customized-dialog-title">
              <BootstrapTooltip title={file.filename}>
                <Typography sx={{ marginRight: '20px' }} variant="h6" noWrap>
                  {file.filename}
                </Typography>
              </BootstrapTooltip>
              <Typography variant="body2" sx={{ marginTop: '5px' }}>
                Uploaded by {file.author}, {dayjs.utc(file.created_at).local().format('lll')}
              </Typography>
              <IconButton
                aria-label="close"
                onClick={onClose}
                sx={{
                  position: 'absolute',
                  right: 8,
                  top: 8,
                  color: theme => theme.palette.secondary.main
                }}
              >
                <CloseIcon />
              </IconButton>
            </DialogTitleStyled>
            <DialogContentStyled dividers>
              {!file.filename.endsWith('.pdf') && <SubHeader />}
              {document && (
                <Box height="100%" maxWidth="2000px" marginX="auto" position="relative" padding="70px 16px 0px">
                  <Grid container spacing={2} height="100%">
                    <Grid item sm={6} md={7} height="100%">
                      <DocumentPreviewContainer>
                        <Button
                          variant="contained"
                          sx={{
                            position: 'absolute',
                            right: '16px',
                            top: '8px',
                            zIndex: 10,
                            color: 'white',
                            background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)',
                            ['&:hover']: { background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)' },
                            '&.Mui-disabled': {
                              color: 'rgba(0, 0, 0, 0.26)',
                              background: 'rgba(0, 0, 0, 0.12)'
                            }
                          }}
                          onClick={() => handleStartParsing(file.id)}
                          disabled={isProcessing}
                          startIcon={isProcessing ? <CircularProgress color="inherit" size={20} /> : null}
                        >
                          Parse with AI
                        </Button>
                        {FileRenderer}
                      </DocumentPreviewContainer>
                    </Grid>
                    <Grid item sm={6} md={5} height="100%">
                      <DialogTitle sx={{ bgcolor: 'primary.main', color: 'secondary.main' }} id="document-dialog-title">
                        Document Details
                      </DialogTitle>
                      <Box
                        sx={{
                          bgcolor: 'white',
                          padding: '16px',
                          height: 'calc(100% - 64px)',
                          overflowY: 'auto',
                          position: 'relative'
                        }}
                      >
                        {fileTermKeysData &&
                          fileTermKeysData.keys.map(
                            ({
                              id,
                              name,
                              value,
                              ai_value,
                              is_poison_pill,
                              poison_pill_detailed,
                              legal_term,
                              comments
                            }) => (
                              <CollapsibleDocumentTermRenderer
                                key={name}
                                id={id}
                                termName={name}
                                aiValue={ai_value}
                                userValue={value}
                                documentId={documentId}
                                siteId={siteId}
                                isPoisonPill={is_poison_pill}
                                poisonPillDetails={poison_pill_detailed}
                                legal_term={legal_term}
                                comments={comments}
                                boardId={boardId}
                                fileId={fileId}
                                taskId={taskId}
                              />
                            )
                          )}
                        <Backdrop
                          sx={{ color: '#1D1D1D', position: 'absolute', bgcolor: 'rgba(250, 250, 250, 0.5)' }}
                          open={isLoadingFileTermKeysData}
                        >
                          <CircularProgress color="inherit" />
                        </Backdrop>
                      </Box>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </DialogContentStyled>
          </DocunentPreviewModalContent>
        </DocunentPreviewModalViewbox>
      </Fade>
    </DocunentPreviewModal>
  );
};

export default DocumentModal;
