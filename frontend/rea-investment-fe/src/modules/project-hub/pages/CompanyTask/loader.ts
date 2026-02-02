import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const taskDetailsQuery = (boardId: number, taskId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['tasks', 'details', { boardId, taskId }],
    queryFn: () => ApiClient.taskManagement.getTaskById(boardId, taskId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const companyBoardsQuery = (companyId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryFn: () => ApiClient.taskManagement.boards('company', companyId),
    queryKey: ['task-boards', { companyId }],
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const companyDetailsQuery = (companyId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['company', 'details', { companyId }],
    queryFn: () => ApiClient.assetManagement.getCompanyById(companyId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const createLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const companyId = params.companyId;
    const taskId = params.taskId;

    const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
    if (!isValidId) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }

    const isValidTaskId = !!taskId && Number.isSafeInteger(Number.parseInt(taskId));
    if (!isValidTaskId) throw new Error(`Provided task id "${taskId}" is invalid.`);

    const companyDetailsPromise = queryClient.fetchQuery(companyDetailsQuery(Number.parseInt(companyId)));
    const boardsPromise = queryClient.fetchQuery(companyBoardsQuery(Number.parseInt(companyId)));

    const [companyDetails, boards] = await Promise.all([companyDetailsPromise, boardsPromise]);

    const [board] = boards.items;

    if (!board) throw new Error(`No task boards found for company ID=${companyId}`);

    const taskDetails = await queryClient.fetchQuery(taskDetailsQuery(board.id, Number.parseInt(taskId)));

    return { companyDetails, taskDetails, board };
  };
