import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Fade from '@mui/material/Fade';
import { useTheme } from '@mui/material/styles';
import EditIcon from '@mui/icons-material/Edit';

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
  hideHeader?: boolean;
}

export const InformationCardBase = <T,>(props: InformationCardBaseProps<T>): React.ReactElement => {
  const { InformationCardForm, informationCardData, siteId, title, hideHeader = false } = props;
  const theme = useTheme();

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

  const borderColor = theme.palette.divider;

  return (
    <Box>
      <Box
        position="relative"
        display="flex"
        flexDirection="column"
        flexGrow={1}
        paddingY={hideHeader ? '8px' : '16px'}
        paddingX="8px"
        border={hideHeader ? 'none' : `1px solid ${borderColor}`}
      >
        {!hideHeader && (
          <>
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
            </Stack>
            <Box px="8px">
              <Divider sx={{ borderBottom: `1px solid ${borderColor}`, height: '1px', marginBottom: '8px' }} />
            </Box>
          </>
        )}
        <InformationCardForm
          ref={formApi}
          mode={mode}
          siteId={siteId}
          setMode={setMode}
          data={informationCardData}
          reflectFormState={setFormReflectedState}
        />
        <Stack
          width="100%"
          direction="row"
          flexWrap="nowrap"
          alignItems="center"
          justifyContent="flex-end"
          sx={{ mt: 1 }}
        >
          {mode === 'view' && (
            <Fade in={mode === 'view'} timeout={{ enter: 300, exit: 300 }}>
              <Button
                data-testid={editBtnTestId}
                variant="outlined"
                size="small"
                startIcon={<EditIcon fontSize="small" />}
                onClick={handleClickEdit}
                sx={{ mx: 1 }}
              >
                Edit
              </Button>
            </Fade>
          )}
          {mode === 'edit' && (
            <Fade in={mode === 'edit'} timeout={{ enter: 300, exit: 300 }}>
              <Stack direction="row" spacing={1} px="8px">
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
