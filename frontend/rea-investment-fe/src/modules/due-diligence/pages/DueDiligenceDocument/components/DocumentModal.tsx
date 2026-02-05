import React, { useEffect, useState, useCallback, useMemo } from 'react';
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
import ButtonGroup from '@mui/material/ButtonGroup';
import Grid from '@mui/material/Grid';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ContentCopyIcon from '@mui/icons-material/ContentCopyOutlined';
import LinkOffIcon from '@mui/icons-material/LinkOff';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import Backdrop from '@mui/material/Backdrop';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';
import Fade from '@mui/material/Fade';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DoneAllIcon from '@mui/icons-material/DoneAll';
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
import {
  ParsingStatusBadge,
  ParseErrorMessage,
  TruncationWarning,
  ParsingMetadata
} from '../../../../../components/common/ParsingStatus';
import PDFViewer from './PDFViewer';

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

interface FileParsingEvidence {
  page?: number | null;
  snippet?: string | null;
  anchor_text?: string | null;
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
  evidence?: FileParsingEvidence | null;
  onViewInDocument?: (page: number, snippet?: string | null, anchorText?: string | null) => void;
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
    taskId,
    evidence,
    onViewInDocument
  } = props;
  const userInputFormRef = React.useRef<DocumentTermUserInputFieldRef | null>(null);
  const [expanded, setExpanded] = React.useState<boolean>(true);

  const copyToTextField = (text: string | null) => {
    if (!text) return;
    const textToPopulate = text.length > 2000 ? text.substring(0, 2000) : text;
    userInputFormRef.current?.setValue && userInputFormRef.current?.setValue(textToPopulate);
  };

  const hasEvidence = evidence && evidence.page != null;

  return (
    <AccordionStyled expanded={expanded} onChange={() => setExpanded(prevExpanded => !prevExpanded)}>
      <AccordionSummaryStyled expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
          <TermName sx={{ flex: 1 }}>{termName}</TermName>
          {hasEvidence ? (
            <BootstrapTooltip
              title={
                evidence.snippet
                  ? `"${evidence.snippet.substring(0, 100)}${evidence.snippet.length > 100 ? '...' : ''}"`
                  : `Found on page ${evidence.page}`
              }
              placement="top"
            >
              <Button
                size="small"
                variant="text"
                onClick={e => {
                  e.stopPropagation();
                  if (onViewInDocument && evidence.page) {
                    onViewInDocument(evidence.page, evidence.snippet, evidence.anchor_text);
                  }
                }}
                sx={{
                  minWidth: 'auto',
                  fontSize: '12px',
                  color: 'primary.main',
                  textTransform: 'none',
                  padding: '2px 8px'
                }}
              >
                Page {evidence.page}
              </Button>
            </BootstrapTooltip>
          ) : (
            <BootstrapTooltip title="No source evidence available for this field" placement="top">
              <Chip
                icon={<LinkOffIcon sx={{ fontSize: '14px !important' }} />}
                label="No evidence"
                size="small"
                variant="outlined"
                sx={{
                  fontSize: '10px',
                  height: '22px',
                  color: 'text.secondary',
                  borderColor: 'divider',
                  '& .MuiChip-icon': { color: 'text.disabled' }
                }}
                onClick={e => e.stopPropagation()}
              />
            </BootstrapTooltip>
          )}
        </Box>
      </AccordionSummaryStyled>
      <AccordionDetails sx={{ display: 'flex', padding: '8px 0 16px 16px' }}>
        <Box flex="1">
          <AIResponseContainer>
            <Typography variant="h6" fontSize="16px" fontWeight="600" py="8px">
              Legal Terms
            </Typography>
            <AIText bgColor>{legal_term}</AIText>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="h6" fontSize="16px" fontWeight="600" py="8px">
                Value
                <BootstrapTooltip title="Copy" placement="top">
                  <IconButton
                    sx={{
                      position: 'absolute',
                      right: '-30px',
                      marginTop: '25px !important',
                      padding: '8px',
                      margin: 0
                    }}
                    onClick={() => copyToTextField(aiValue)}
                  >
                    <ContentCopyIcon sx={{ fontSize: '20px', color: theme => theme.palette.text.secondary }} />
                  </IconButton>
                </BootstrapTooltip>
              </Typography>
            </Box>
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
  const [currentRunId, setCurrentRunId] = useState<number | undefined>();
  const [currentCorrelationId, setCurrentCorrelationId] = useState<string | undefined>();
  const [verifyIndex, setVerifyIndex] = useState<number>(-1);
  const [isVerifyMode, setIsVerifyMode] = useState(false);
  const [showAcceptDialog, setShowAcceptDialog] = useState(false);
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

  const { mutateAsync: startParsing, isPending: isStartingParse } = useMutation({
    mutationFn: ({ id, forceReprocess }: { id: number; forceReprocess: boolean }) =>
      ApiClient.dueDiligence.documentStartParsing(id, siteId, documentId, forceReprocess),
    onSuccess: response => {
      setCurrentRunId(response.run_id);
      setCurrentCorrelationId(response.correlation_id);
      notify(`Parsing started. This may take a few minutes.`);
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
    queryKey: ['document-status', { siteId, documentId, fileId }],
    enabled: open && fileId !== -1,
    refetchInterval: isProcessing ? 5000 : false
  });

  const handleStartParsing = useCallback(
    async (fileIdToProcess: number, forceReprocess = false) => {
      try {
        await startParsing({ id: fileIdToProcess, forceReprocess });
      } catch (e) {
        console.log(e);
      }
    },
    [startParsing]
  );

  const handleReprocess = useCallback(() => {
    if (fileId !== -1) {
      handleStartParsing(fileId, true);
    }
  }, [fileId, handleStartParsing]);

  const { data: parseRunHistory } = useQuery({
    queryKey: ['parse-run-history', siteId, documentId, fileId],
    queryFn: () => ApiClient.dueDiligence.getParseRunHistory({ siteId, documentId, fileId }),
    enabled: fileId !== -1,
    staleTime: 30000
  });

  const [selectedRunId, setSelectedRunId] = useState<number | undefined>();
  const [showParseHistory, setShowParseHistory] = useState(false);

  useEffect(() => {
    if (currentRunId) {
      setSelectedRunId(currentRunId);
    } else if (parseRunHistory?.runs?.length) {
      const latestRun = parseRunHistory.runs.find(r => r.is_latest);
      if (latestRun) setSelectedRunId(latestRun.id);
    }
  }, [currentRunId, parseRunHistory]);

  const selectedRun = useMemo(() => {
    if (!selectedRunId || !parseRunHistory?.runs) return null;
    return parseRunHistory.runs.find(r => r.id === selectedRunId) || null;
  }, [selectedRunId, parseRunHistory]);

  const isSelectedRunLatest = selectedRun?.is_latest ?? true;
  const runStatusLower = selectedRun?.status?.toLowerCase().replace(/\s+/g, '_');
  const isSelectedRunSucceeded = runStatusLower === 'completed' || runStatusLower === 'succeeded';
  const canAcceptFromSelectedRun = isSelectedRunSucceeded && isSelectedRunLatest;

  const { mutateAsync: bulkAccept, isPending: isBulkAccepting } = useMutation({
    mutationFn: (fields: Array<{ field_name: string; value: string | null }>) =>
      ApiClient.dueDiligence.bulkAcceptAIValues({
        siteId,
        documentId,
        fileId,
        runId: selectedRunId!,
        fields,
        allowAcceptNonLatest: false
      }),
    onSuccess: response => {
      notify(response.message);
      queryClient.invalidateQueries({ queryKey: ['document-terms'] });
      setShowAcceptDialog(false);
    },
    onError: (error: AxiosError<{ detail?: string }>) => {
      const detail = error.response?.data?.detail || 'Something went wrong while accepting values.';
      notify(detail);
    }
  });

  const fieldsToAccept = useMemo(() => {
    if (!fileTermKeysData?.keys) return [];
    return fileTermKeysData.keys
      .filter((field): field is typeof field & { ai_value: string } => !!field.ai_value && !field.value)
      .map(field => ({ field_name: field.name, value: field.ai_value }));
  }, [fileTermKeysData]);

  const fieldsWithoutEvidence = useMemo(() => {
    if (!fieldsToAccept.length || !fileTermKeysData?.keys) return 0;
    return fileTermKeysData.keys.filter(field => field.ai_value && !field.value && !field.evidence?.page).length;
  }, [fieldsToAccept, fileTermKeysData]);

  const handleAcceptAll = useCallback(() => {
    if (fieldsToAccept.length === 0) {
      notify('No AI values to accept');
      return;
    }
    setShowAcceptDialog(true);
  }, [fieldsToAccept, notify]);

  const handleConfirmAccept = useCallback(() => {
    bulkAccept(fieldsToAccept);
  }, [bulkAccept, fieldsToAccept]);

  useEffect(() => {
    if (!documentStatus) return;

    const status = documentStatus.status?.toLowerCase().replace(/\s+/g, '_');

    if (documentStatus.run_id) {
      setCurrentRunId(documentStatus.run_id);
    }
    if (documentStatus.correlation_id) {
      setCurrentCorrelationId(documentStatus.correlation_id);
    }

    if (status === 'processing_failed' || status === 'failed') {
      setIsProcessing(false);
    } else if (status === 'completed' || status === 'succeeded') {
      if (isProcessing) {
        notify('Processing completed');
        queryClient.invalidateQueries({ queryKey: ['document-terms'] });
      }
      setIsProcessing(false);
    } else if (status === 'processing' || status === 'queued') {
      setIsProcessing(true);
    } else {
      setIsProcessing(false);
    }
  }, [documentStatus, isProcessing, notify, queryClient]);

  const parsingStatus = documentStatus?.status?.toLowerCase().replace(/\s+/g, '_') || 'not_started';
  const hasFailed = parsingStatus === 'processing_failed' || parsingStatus === 'failed';
  const hasCompleted = parsingStatus === 'completed' || parsingStatus === 'succeeded';

  React.useEffect(() => {
    if (fileTermKeysDataLoadingError) {
      notify(
        fileTermKeysDataLoadingError instanceof AxiosError
          ? fileTermKeysDataLoadingError.response?.data?.message || fileTermKeysDataLoadingError.message
          : fileTermKeysDataLoadingError.message
      );
    }
  }, [notify, fileTermKeysDataLoadingError]);

  const [pdfTargetPage, setPdfTargetPage] = useState<number | undefined>(undefined);
  const [pdfTargetSearchText, setPdfTargetSearchText] = useState<string | undefined>(undefined);
  const [pdfNavigationTrigger, setPdfNavigationTrigger] = useState<number>(0);

  const getFileType = (filename: string): string | undefined => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return 'pdf';
    if (ext === 'docx') return 'docx';
    if (ext === 'doc') return 'doc';
    if (ext === 'png') return 'png';
    if (ext === 'jpg' || ext === 'jpeg') return 'jpg';
    return undefined;
  };

  const isPDF = file && getFileType(file.filename) === 'pdf';

  const handleViewInDocument = useCallback(
    (page: number, snippet?: string | null, anchorText?: string | null) => {
      if (!isPDF) {
        notify('Jump-to-page is available for PDFs only');
        return;
      }
      const searchText = anchorText || snippet;
      setPdfTargetPage(page);
      setPdfTargetSearchText(searchText || undefined);
      setPdfNavigationTrigger(prev => prev + 1);
      notify(`Jumped to page ${page}`);
    },
    [isPDF, notify]
  );

  const fieldsWithEvidence = useMemo(() => {
    if (!fileTermKeysData?.keys) return [];
    return fileTermKeysData.keys
      .map((field, index) => ({ ...field, originalIndex: index }))
      .filter(field => field.evidence?.page != null);
  }, [fileTermKeysData]);

  const handleStartVerify = useCallback(() => {
    if (fieldsWithEvidence.length === 0) {
      notify('No fields with evidence to verify');
      return;
    }
    if (!isPDF) {
      notify('Verify all is available for PDFs only');
      return;
    }
    setIsVerifyMode(true);
    setVerifyIndex(0);
    const firstField = fieldsWithEvidence[0];
    if (firstField.evidence?.page) {
      handleViewInDocument(firstField.evidence.page, firstField.evidence.snippet, firstField.evidence.anchor_text);
      notify(`Verifying field 1 of ${fieldsWithEvidence.length}: ${firstField.name}`);
    }
  }, [fieldsWithEvidence, isPDF, handleViewInDocument, notify]);

  const handleVerifyNext = useCallback(() => {
    if (verifyIndex >= fieldsWithEvidence.length - 1) {
      notify('All fields verified!');
      setIsVerifyMode(false);
      setVerifyIndex(-1);
      return;
    }
    const nextIndex = verifyIndex + 1;
    setVerifyIndex(nextIndex);
    const nextField = fieldsWithEvidence[nextIndex];
    if (nextField.evidence?.page) {
      handleViewInDocument(nextField.evidence.page, nextField.evidence.snippet, nextField.evidence.anchor_text);
      notify(`Verifying field ${nextIndex + 1} of ${fieldsWithEvidence.length}: ${nextField.name}`);
    }
  }, [verifyIndex, fieldsWithEvidence, handleViewInDocument, notify]);

  const handleVerifyPrev = useCallback(() => {
    if (verifyIndex <= 0) return;
    const prevIndex = verifyIndex - 1;
    setVerifyIndex(prevIndex);
    const prevField = fieldsWithEvidence[prevIndex];
    if (prevField.evidence?.page) {
      handleViewInDocument(prevField.evidence.page, prevField.evidence.snippet, prevField.evidence.anchor_text);
      notify(`Verifying field ${prevIndex + 1} of ${fieldsWithEvidence.length}: ${prevField.name}`);
    }
  }, [verifyIndex, fieldsWithEvidence, handleViewInDocument, notify]);

  const handleStopVerify = useCallback(() => {
    setIsVerifyMode(false);
    setVerifyIndex(-1);
  }, []);

  const renderFileViewer = () => {
    if (!file || !fileUrl) return null;

    if (isPDF) {
      return (
        <PDFViewer
          fileUrl={fileUrl}
          targetPage={pdfTargetPage}
          targetSearchText={pdfTargetSearchText}
          navigationTrigger={pdfNavigationTrigger}
        />
      );
    }

    return (
      <DocViewer
        pluginRenderers={DocViewerRenderers}
        documents={[{ uri: fileUrl, fileType: getFileType(file.filename) }]}
        style={{ width: '100%', height: '100%' }}
        config={{
          header: {
            disableHeader: true,
            disableFileName: true
          },
          pdfVerticalScrollByDefault: true
        }}
      />
    );
  };

  if (!file || !fileUrl) return null;

  return (
    <>
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
                          <Box
                            sx={{
                              position: 'absolute',
                              right: '16px',
                              top: '8px',
                              zIndex: 10,
                              display: 'flex',
                              gap: 1
                            }}
                          >
                            {hasCompleted &&
                              isPDF &&
                              fieldsWithEvidence.length > 0 &&
                              (isVerifyMode ? (
                                <ButtonGroup variant="contained" size="small">
                                  <Button
                                    onClick={handleVerifyPrev}
                                    disabled={verifyIndex <= 0}
                                    sx={{ minWidth: 'auto', px: 1 }}
                                  >
                                    <NavigateBeforeIcon fontSize="small" />
                                  </Button>
                                  <Button
                                    sx={{
                                      pointerEvents: 'none',
                                      bgcolor: 'primary.main',
                                      minWidth: '80px'
                                    }}
                                  >
                                    {verifyIndex + 1} / {fieldsWithEvidence.length}
                                  </Button>
                                  <Button onClick={handleVerifyNext} sx={{ minWidth: 'auto', px: 1 }}>
                                    <NavigateNextIcon fontSize="small" />
                                  </Button>
                                  <Button onClick={handleStopVerify} color="error" sx={{ minWidth: 'auto', px: 1 }}>
                                    <CloseIcon fontSize="small" />
                                  </Button>
                                </ButtonGroup>
                              ) : (
                                <Button
                                  variant="outlined"
                                  size="small"
                                  onClick={handleStartVerify}
                                  startIcon={<FactCheckIcon />}
                                  sx={{ bgcolor: 'white' }}
                                >
                                  Verify All ({fieldsWithEvidence.length})
                                </Button>
                              ))}
                            <Button
                              variant="contained"
                              sx={{
                                color: 'white',
                                background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)',
                                ['&:hover']: { background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)' },
                                '&.Mui-disabled': {
                                  color: 'rgba(0, 0, 0, 0.26)',
                                  background: 'rgba(0, 0, 0, 0.12)'
                                }
                              }}
                              onClick={() => handleStartParsing(file.id, hasCompleted || hasFailed)}
                              disabled={isProcessing || isStartingParse}
                              startIcon={
                                isProcessing || isStartingParse ? <CircularProgress color="inherit" size={20} /> : null
                              }
                            >
                              {hasCompleted || hasFailed ? 'Reprocess' : 'Parse with AI'}
                            </Button>
                          </Box>
                          {renderFileViewer()}
                        </DocumentPreviewContainer>
                      </Grid>
                      <Grid item sm={6} md={5} height="100%">
                        <DialogTitle
                          sx={{
                            bgcolor: 'primary.main',
                            color: 'secondary.main',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                          }}
                          id="document-dialog-title"
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <span>Document Details</span>
                            {documentStatus && <ParsingStatusBadge status={parsingStatus} />}
                          </Box>
                          {hasCompleted && fieldsToAccept.length > 0 && (
                            <BootstrapTooltip
                              title={
                                !canAcceptFromSelectedRun
                                  ? !isSelectedRunSucceeded
                                    ? 'Cannot accept from a non-succeeded run'
                                    : 'Cannot accept from a non-latest run'
                                  : ''
                              }
                            >
                              <span>
                                <Button
                                  variant="contained"
                                  size="small"
                                  color="success"
                                  onClick={handleAcceptAll}
                                  disabled={isBulkAccepting || !canAcceptFromSelectedRun || !selectedRunId}
                                  startIcon={
                                    isBulkAccepting ? <CircularProgress size={16} color="inherit" /> : <DoneAllIcon />
                                  }
                                  sx={{ fontSize: '12px' }}
                                >
                                  Accept All ({fieldsToAccept.length})
                                </Button>
                              </span>
                            </BootstrapTooltip>
                          )}
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
                          {hasFailed && (
                            <ParseErrorMessage errorMessage={documentStatus?.error_message} onRetry={handleReprocess} />
                          )}
                          {hasCompleted && documentStatus?.was_truncated && (
                            <TruncationWarning
                              wasTruncated={documentStatus.was_truncated}
                              truncatedCharCount={documentStatus.truncated_char_count}
                              charCount={documentStatus.char_count}
                            />
                          )}
                          {hasCompleted && (
                            <ParsingMetadata
                              charCount={documentStatus?.char_count}
                              wordCount={documentStatus?.word_count}
                              pageCount={documentStatus?.page_count}
                              correlationId={currentCorrelationId}
                              runId={currentRunId}
                              showDebugInfo={true}
                            />
                          )}
                          {parseRunHistory && parseRunHistory.runs.length > 0 && (
                            <AccordionStyled
                              expanded={showParseHistory}
                              onChange={() => setShowParseHistory(!showParseHistory)}
                              sx={{ mb: 2 }}
                            >
                              <AccordionSummaryStyled expandIcon={<ExpandMoreIcon />}>
                                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                  Parse History ({parseRunHistory.runs.length} runs)
                                </Typography>
                              </AccordionSummaryStyled>
                              <AccordionDetails sx={{ p: 0 }}>
                                <Box sx={{ maxHeight: 200, overflowY: 'auto' }}>
                                  {parseRunHistory.runs.map(run => (
                                    <Box
                                      key={run.id}
                                      onClick={() => setSelectedRunId(run.id)}
                                      sx={{
                                        p: 1.5,
                                        cursor: 'pointer',
                                        borderBottom: '1px solid #eee',
                                        bgcolor: selectedRunId === run.id ? 'action.selected' : 'transparent',
                                        '&:hover': { bgcolor: 'action.hover' }
                                      }}
                                    >
                                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                          Run #{run.extraction_run_number || run.id}
                                        </Typography>
                                        {run.is_latest && (
                                          <Chip
                                            label="Latest"
                                            size="small"
                                            color="primary"
                                            sx={{ height: 20, fontSize: '10px' }}
                                          />
                                        )}
                                        <Chip
                                          label={run.status}
                                          size="small"
                                          color={(() => {
                                            const s = run.status?.toLowerCase().replace(/\s+/g, '_');
                                            if (s === 'completed' || s === 'succeeded') return 'success';
                                            if (s === 'processing' || s === 'queued') return 'warning';
                                            return 'error';
                                          })()}
                                          sx={{ height: 20, fontSize: '10px' }}
                                        />
                                        {run.was_truncated && (
                                          <Chip
                                            label="Truncated"
                                            size="small"
                                            color="warning"
                                            sx={{ height: 20, fontSize: '10px' }}
                                          />
                                        )}
                                      </Box>
                                      <Typography variant="caption" color="text.secondary">
                                        {run.created_at
                                          ? dayjs(run.created_at).format('MMM D, YYYY h:mm A')
                                          : 'Unknown date'}
                                        {run.error_message && (
                                          <span style={{ color: 'red', marginLeft: 8 }}>
                                            {run.error_message.match(/\[(\w+)\]/)?.[1] || 'Error'}
                                          </span>
                                        )}
                                      </Typography>
                                      {selectedRunId === run.id && run.correlation_id && (
                                        <Typography
                                          variant="caption"
                                          color="text.secondary"
                                          sx={{ display: 'block', mt: 0.5 }}
                                        >
                                          Correlation: {run.correlation_id}
                                        </Typography>
                                      )}
                                    </Box>
                                  ))}
                                </Box>
                              </AccordionDetails>
                            </AccordionStyled>
                          )}
                          {selectedRun && !isSelectedRunLatest && (
                            <Box
                              sx={{
                                p: 1.5,
                                mb: 2,
                                bgcolor: 'warning.light',
                                borderRadius: 1,
                                color: 'warning.contrastText'
                              }}
                            >
                              <Typography variant="body2">
                                Viewing older run #{selectedRun.extraction_run_number || selectedRun.id}. Accept is
                                disabled for non-latest runs.
                              </Typography>
                            </Box>
                          )}
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
                                comments,
                                evidence
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
                                  evidence={evidence}
                                  onViewInDocument={handleViewInDocument}
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
      <Dialog open={showAcceptDialog} onClose={() => setShowAcceptDialog(false)}>
        <DialogTitle>Accept All AI Values</DialogTitle>
        <DialogContent>
          <DialogContentText>
            You are about to accept <strong>{fieldsToAccept.length}</strong> AI-extracted values.
            {fieldsWithoutEvidence > 0 && (
              <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
                Note: {fieldsWithoutEvidence} field(s) have no source evidence and cannot be verified in the document.
              </Box>
            )}
          </DialogContentText>
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              This will copy the AI values to the user input fields for all fields that do not already have a user
              value.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAcceptDialog(false)} disabled={isBulkAccepting}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmAccept}
            variant="contained"
            color="success"
            disabled={isBulkAccepting}
            startIcon={isBulkAccepting ? <CircularProgress size={16} color="inherit" /> : <DoneAllIcon />}
          >
            {isBulkAccepting ? 'Accepting...' : 'Confirm Accept'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default DocumentModal;
