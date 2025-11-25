import { LoaderFunction, LoaderFunctionArgs, redirect } from 'react-router-dom';
import { ApiClient } from '../../api';

export const withAuthControl = (load: LoaderFunction) => async (args: LoaderFunctionArgs) => {
  try {
    const loadedData = await load(args);
    return loadedData;
  } catch (e) {
    const token = ApiClient._tokenManager.getAuthToken();
    if (token === null) {
      return redirect('/login');
    } else {
      throw e;
    }
  }
};
