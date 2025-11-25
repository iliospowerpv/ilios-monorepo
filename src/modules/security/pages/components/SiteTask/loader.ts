import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../../api';
import { siteDetailsQuery } from '../../../../asset-management/loaders/site-details-loader';

export const taskDetailsQuery = (boardId: number, taskId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['tasks', 'details', { boardId, taskId }],
    queryFn: () => ApiClient.taskManagement.getTaskById(boardId, taskId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const siteBoardsQuery = (siteId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryFn: () => ApiClient.taskManagement.boards('site', siteId, { module: 'O&M' }),
    queryKey: ['task-boards', { siteId }],
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const siteCrumbsQuery = (siteId: number, enabled = true) =>
  queryOptions({
    queryKey: ['site', 'crumbs', 'O&M (Production Monitoring)', { siteId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: siteId,
        entity_type: 'site',
        permission_module: 'O&M (Production Monitoring)'
      }),
    enabled: enabled
  });

export const companyDetailsQuery = (companyId: number, enabled = true) =>
  queryOptions({
    queryKey: ['company', 'crumbs', 'O&M (Production Monitoring)', { companyId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: companyId,
        entity_type: 'company',
        permission_module: 'O&M (Production Monitoring)'
      }),
    enabled: enabled
  });

export const summaryDetailsQuery = (boardId: number, taskId: string, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['tasks', 'summary', { boardId, taskId }],
    queryFn: () => ApiClient.taskManagement.getSiteVisit(boardId, taskId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export { siteDetailsQuery };

export const createLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const siteId = params.siteId;
    const taskId = params.taskId;
    const companyId = params.companyId;

    const isValidSiteId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
    if (!isValidSiteId) throw new Error(`Provided site id "${siteId}" is invalid.`);

    const isValidTaskId = !!taskId && Number.isSafeInteger(Number.parseInt(taskId));
    if (!isValidTaskId) throw new Error(`Provided task id "${taskId}" is invalid.`);

    const isValid = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
    if (!isValid) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }

    const loadBoards = () => queryClient.fetchQuery(siteBoardsQuery(Number.parseInt(siteId)));
    const siteData = await queryClient.fetchQuery(siteCrumbsQuery(Number.parseInt(siteId)));
    const companyData = await queryClient.fetchQuery(companyDetailsQuery(Number.parseInt(companyId)));
    const [boards] = await Promise.all([loadBoards()]);

    const [board] = boards.items;

    if (!board) throw new Error(`No task boards found for site ID=${siteId}`);

    const taskDetails = await queryClient.fetchQuery(taskDetailsQuery(board.id, Number.parseInt(taskId)));

    return { siteData, taskDetails, board, companyData };
  };
