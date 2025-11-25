import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import Zoom from '@mui/material/Zoom';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Fade from '@mui/material/Fade';

export interface InformationCardFormReflectedState {
  isValid: boolean;
  isDirty: boolean;
  isSubmitting: boolean;
}

export interface InformationCardFormRef {
  resetForm: () => void;
  submit: () => void;
}

export interface InformationCardFormProps<T> {
  mode: 'view' | 'edit';
  siteId: number;
  data: T;
  reflectFormState: (state: InformationCardFormReflectedState) => void;
  setMode: React.Dispatch<React.SetStateAction<'view' | 'edit'>>;
}

interface InformationCardBaseProps<T> {
  informationCardData: T;
  InformationCardForm: React.ForwardRefExoticComponent<
    InformationCardFormProps<T> & React.RefAttributes<InformationCardFormRef>
  >;
  siteId: number;
  title: string;
}

export const InformationCardBase = <T,>(props: InformationCardBaseProps<T>): React.ReactElement => {
  const { InformationCardForm, informationCardData, siteId, title } = props;

  const [mode, setMode] = React.useState<'view' | 'edit'>('view');
  const [formReflectedState, setFormReflectedState] = React.useState<InformationCardFormReflectedState>({
    isValid: false,
    isDirty: false,
    isSubmitting: false
  });
  const formApi = React.useRef<InformationCardFormRef | null>(null);

  const { isValid, isDirty, isSubmitting } = formReflectedState;

  const handleClickEdit = () => setMode('edit');

  const handleClickCancel = () => {
    formApi.current && formApi.current.resetForm();
    setMode('view');
  };

  const handleClickSave = () => {
    formApi.current && formApi.current.submit();
  };

  const editBtnTestId = title.toLocaleLowerCase().split(' ').join('_') + '-edit-btn';

  return (
    <Box>
      <Box
        position="relative"
        display="flex"
        flexDirection="column"
        flexGrow={1}
        paddingY="16px"
        paddingX="8px"
        border="1px solid #0000003B"
      >
        <Stack
          direction="row"
          p="8px"
          pt="0px"
          pb="12px"
          flexWrap="nowrap"
          justifyContent="space-between"
          alignItems="center"
        >
          <Typography variant="h6" mb="0px">
            {title}
          </Typography>
          <Zoom in={mode === 'view'}>
            <Box borderRadius="50%" bgcolor="rgba(255, 255, 255, 0.85)">
              <IconButton data-testid={editBtnTestId} size="small" onClick={handleClickEdit}>
                <EditIcon fontSize="small" sx={{ color: '#404251' }} />
              </IconButton>
            </Box>
          </Zoom>
        </Stack>
        <Box px="8px">
          <Divider sx={{ borderBottom: '1px solid #0000003B', height: '1px', marginBottom: '8px' }} />
        </Box>
        <InformationCardForm
          ref={formApi}
          mode={mode}
          siteId={siteId}
          setMode={setMode}
          data={informationCardData}
          reflectFormState={setFormReflectedState}
        />
        <Stack width="100%" direction="row" flexWrap="nowrap" alignItems="center" justifyContent="flex-end">
          {mode === 'edit' && (
            <Fade in={mode === 'edit'} timeout={{ enter: 1000, exit: 1000 }}>
              <Stack direction="row" spacing={1} px="8px" pt="16px">
                <Button disabled={isSubmitting} variant="outlined" size="small" onClick={handleClickCancel}>
                  Cancel
                </Button>
                <Button
                  disabled={!isValid || !isDirty || isSubmitting}
                  variant="contained"
                  size="small"
                  onClick={handleClickSave}
                >
                  Save
                </Button>
              </Stack>
            </Fade>
          )}
        </Stack>
      </Box>
    </Box>
  );
};

export default InformationCardBase;
