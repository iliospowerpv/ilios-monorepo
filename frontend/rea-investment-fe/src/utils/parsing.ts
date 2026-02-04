export type ParsingStatus = 'queued' | 'processing' | 'completed' | 'processing_failed' | 'not_started';

export type ParsingReasonCode =
  | 'file_too_large'
  | 'too_many_pages'
  | 'insufficient_text_extracted'
  | 'unsupported_file_type'
  | 'text_extraction_failed'
  | 'llm_call_failed'
  | 'no_extraction_config'
  | 'storage_error';

export interface ParsingStatusResponse {
  status: ParsingStatus;
  run_id?: number;
  correlation_id?: string;
  error_message?: string;
  char_count?: number;
  word_count?: number;
  page_count?: number;
  was_truncated?: boolean;
  truncated_char_count?: number;
}

export interface ParseTriggerResponse {
  run_id: number;
  correlation_id: string;
  status: ParsingStatus;
  code: number;
  message: string;
}

const REASON_CODE_MESSAGES: Record<ParsingReasonCode, string> = {
  insufficient_text_extracted:
    'This document appears to be scanned or contains mostly images. OCR processing may be required.',
  file_too_large: 'This file exceeds the maximum supported size. Please upload a smaller file.',
  too_many_pages: 'This PDF exceeds the maximum supported page count.',
  unsupported_file_type: 'This file type is not supported for AI parsing.',
  text_extraction_failed: 'Unable to extract text from this document. The file may be corrupted.',
  llm_call_failed: 'AI parsing failed. Please try again.',
  no_extraction_config: 'No parsing configuration found for this document type.',
  storage_error: 'Unable to read file from storage. Please try re-uploading.'
};

export function extractReasonCode(errorMessage?: string): ParsingReasonCode | null {
  if (!errorMessage) return null;

  const match = errorMessage.match(/\[([a-z_]+)\]/);
  if (match && match[1]) {
    const code = match[1] as ParsingReasonCode;
    if (code in REASON_CODE_MESSAGES) {
      return code;
    }
  }
  return null;
}

export function getErrorMessageForReasonCode(reasonCode: ParsingReasonCode | null): string {
  if (!reasonCode) {
    return 'An unexpected error occurred during parsing. Please try again.';
  }
  return REASON_CODE_MESSAGES[reasonCode] || 'An unexpected error occurred during parsing. Please try again.';
}

export function getStatusDisplayInfo(status: ParsingStatus | string): {
  label: string;
  color: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';
  isLoading: boolean;
} {
  const normalizedStatus = status.toLowerCase().replace(/\s+/g, '_');

  switch (normalizedStatus) {
    case 'queued':
      return { label: 'Queued', color: 'info', isLoading: false };
    case 'processing':
      return { label: 'Processing', color: 'primary', isLoading: true };
    case 'completed':
    case 'succeeded':
      return { label: 'Completed', color: 'success', isLoading: false };
    case 'processing_failed':
    case 'failed':
      return { label: 'Failed', color: 'error', isLoading: false };
    case 'not_started':
    default:
      return { label: 'Not Started', color: 'default', isLoading: false };
  }
}

export function formatCharCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`;
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
}
