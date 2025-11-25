import { render, screen } from '@testing-library/react';
import { DocImageRenderer } from '../../../../components/common/DocImageRenderer/DocImageRenderer';

describe('DocImageRenderer page', () => {
  it('should render and function correctly', () => {
    const observeMock = jest.fn();
    const unobserveMock = jest.fn();
    const disconnectMock = jest.fn();

    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    global.ResizeObserver = function () {
      return {
        observe: observeMock,
        unobserve: unobserveMock,
        disconnect: disconnectMock
      };
    };

    render(
      <DocImageRenderer
        mainState={{
          currentFileNo: 1,
          documents: [],
          language: 'en',
          currentDocument: {
            uri: '',
            fileData: 'https://www.google.com.ua/images/branding/googlelogo/1x/googlelogo_light_color_272x92dp.png'
          }
        }}
      />
    );

    const container = screen.getByTestId('doc-image-renderer-container');
    expect(container).toBeInTheDocument();
  });
});
