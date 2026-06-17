import { buildAssumptionsApi } from '../assumptions';

const makeHttp = () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn()
});

describe('buildAssumptionsApi', () => {
  it('getActiveFacts issues a GET to the facts URL', async () => {
    const http = makeHttp();
    const payload = { site_id: 123, facts: [], total: 0 };
    http.get.mockResolvedValue({ data: payload });

    const api = buildAssumptionsApi(http as any);
    const result = await api.getActiveFacts(123);

    expect(http.get).toHaveBeenCalledTimes(1);
    expect(http.get).toHaveBeenCalledWith('/api/projects/123/assumptions/facts');
    expect(result).toEqual(payload);
    expect(http.post).not.toHaveBeenCalled();
  });

  it('getCandidateFacts issues a GET to the candidates URL for a file', async () => {
    const http = makeHttp();
    http.get.mockResolvedValue({ data: { site_id: 123, facts: [], total: 0 } });

    const api = buildAssumptionsApi(http as any);
    await api.getCandidateFacts(123, 9);

    expect(http.get).toHaveBeenCalledWith('/api/projects/123/assumptions/facts/candidates/9');
  });

  it('getPromotionDiff POSTs the file_id to the diff URL', async () => {
    const http = makeHttp();
    const diff = { has_changes: true, changes: [], summary: { added: 0, changed: 0, removed: 0 } };
    http.post.mockResolvedValue({ data: diff });

    const api = buildAssumptionsApi(http as any);
    const result = await api.getPromotionDiff(123, 9);

    expect(http.post).toHaveBeenCalledTimes(1);
    expect(http.post).toHaveBeenCalledWith('/api/projects/123/assumptions/promotion/diff', { file_id: 9 });
    expect(result).toEqual(diff);
  });

  it('promoteVersion POSTs the full payload to the promote URL', async () => {
    const http = makeHttp();
    const response = {
      promoted: true,
      file_id: 9,
      document_id: 5,
      promotion_id: 100,
      facts_promoted: 2,
      diff: { has_changes: true, changes: [], summary: { added: 1, changed: 1, removed: 0 } }
    };
    http.post.mockResolvedValue({ data: response });

    const api = buildAssumptionsApi(http as any);
    const result = await api.promoteVersion(123, { document_id: 5, file_id: 9, notes: 'looks good' });

    expect(http.post).toHaveBeenCalledTimes(1);
    expect(http.post).toHaveBeenCalledWith('/api/projects/123/assumptions/promote', {
      document_id: 5,
      file_id: 9,
      notes: 'looks good'
    });
    expect(result).toEqual(response);
  });

  it('getPromotionHistory issues a GET to the promotions URL', async () => {
    const http = makeHttp();
    http.get.mockResolvedValue({ data: { site_id: 123, promotions: [] } });

    const api = buildAssumptionsApi(http as any);
    await api.getPromotionHistory(123);

    expect(http.get).toHaveBeenCalledWith('/api/projects/123/assumptions/promotions');
  });
});
