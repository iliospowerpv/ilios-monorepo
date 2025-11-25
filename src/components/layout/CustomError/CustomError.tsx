import React from 'react';
import { AxiosError } from 'axios';
import { useRouteError, isRouteErrorResponse } from 'react-router-dom';

import Error403 from './Error403/Error403';
import Error404 from './Error404/Error404';
import GeneralError from './GeneralError/GeneralError';
import { ContainerStyled } from './CustomError.styles';

const CustomError: React.FC = () => {
  const error = useRouteError() as Error;
  let ErrorComponent;

  if (isRouteErrorResponse(error)) {
    if (error.status === 404) {
      ErrorComponent = <Error404 />;
    } else if (error.status === 403) {
      ErrorComponent = <Error403 />;
    } else {
      ErrorComponent = <GeneralError message={error?.message} />;
    }
  } else {
    if ((error as AxiosError)?.response?.status === 404) {
      ErrorComponent = <Error404 />;
    } else if ((error as AxiosError)?.response?.status === 403) {
      ErrorComponent = <Error403 />;
    } else {
      ErrorComponent = <GeneralError message={error?.message} />;
    }
  }

  return <ContainerStyled data-testid="custom-error__component">{ErrorComponent}</ContainerStyled>;
};

export default CustomError;
