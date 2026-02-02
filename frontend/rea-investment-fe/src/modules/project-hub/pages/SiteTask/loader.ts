import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';
import { createSiteDetailsLoader, siteDetailsQuery } from '../../loaders/site-details-loader';

export const taskDetailsQuery = (boardId: number, taskId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['tasks', 'details', { boardId, taskId }],
    queryFn: () => ApiClient.taskManagement.getTaskById(boardId, taskId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const siteBoardsQuery = (siteId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryFn: () => ApiClient.taskManagement.boards('site', siteId),
    queryKey: ['task-boards', { siteId }],
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export { siteDetailsQuery };

export const createLoader =
  (queryClient: QueryClient) =>
  async ({ params, request }: LoaderFunctionArgs) => {
    const siteId = params.siteId;
    const taskId = params.taskId;

    const isValidSiteId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
    if (!isValidSiteId) throw new Error(`Provided site id "${siteId}" is invalid.`);

    const isValidTaskId = !!taskId && Number.isSafeInteger(Number.parseInt(taskId));
    if (!isValidTaskId) throw new Error(`Provided task id "${taskId}" is invalid.`);

    const loadSiteDetails = createSiteDetailsLoader(queryClient);
    const loadBoards = () => queryClient.fetchQuery(siteBoardsQuery(Number.parseInt(siteId)));

    const [siteData, boards] = await Promise.all([loadSiteDetails({ params, request }), loadBoards()]);

    const [board] = boards.items;

    if (!board) throw new Error(`No task boards found for site ID=${siteId}`);

    const taskDetails = await queryClient.fetchQuery(taskDetailsQuery(board.id, Number.parseInt(taskId)));

    return { siteData, taskDetails, board };
  };
