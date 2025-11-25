import React from 'react';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import Collapse from '@mui/material/Collapse';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Zoom from '@mui/material/Zoom';

export type DescriptionFormFields = {
  description: string | null;
};

export type DescriptionFormSubmitHandler = SubmitHandler<DescriptionFormFields>;

interface DescriptionProps {
  descriptionText: string | null;
  onSubmitEdit: DescriptionFormSubmitHandler;
  maxLength?: number;
  name?: string;
}

export const UniversalDescription: React.FC<DescriptionProps> = ({
  descriptionText,
  onSubmitEdit,
  maxLength = 200,
  name = 'Description'
}) => {
  const { handleSubmit, formState, setFocus, control, reset } = useForm<DescriptionFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: { description: descriptionText }
  });

  const mode: 'add' | 'edit' = React.useMemo(() => (descriptionText === null ? 'add' : 'edit'), [descriptionText]);

  React.useEffect(() => {
    reset({ description: descriptionText });
    setIsEditing(false);
  }, [descriptionText, reset]);

  const [isEditing, setIsEditing] = React.useState<boolean>(false);

  React.useEffect(() => {
    isEditing && setFocus('description');
  }, [isEditing, setFocus]);

  const handleClickEdit = () => {
    setIsEditing(true);
  };

  const handleCancelClick = () => {
    reset();
    mode === 'edit' && setIsEditing(false);
  };

  const onBlurHandler = (onBlur: () => void) => () => {
    !isDirty && setIsEditing(false);
    onBlur();
  };

  const { errors, isValid, isSubmitting, isDirty } = formState;

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmitEdit)}>
      <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
        {name}
      </Typography>
      <Box position="relative">
        <Controller
          name="description"
          control={control}
          rules={{
            maxLength: {
              value: maxLength,
              message: `${name ? name.charAt(0).toUpperCase() + name.slice(1) : 'Description'} length should not exceed the limit of ${maxLength} characters.`
            }
          }}
          render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
            <TextField
              {...field}
              fullWidth
              size="small"
              placeholder={`Add ${name}...`}
              helperText={errors.description?.message}
              error={!!errors.description}
              multiline
              minRows={6}
              disabled={mode === 'edit' && !isEditing}
              inputRef={ref}
              InputProps={{
                sx: {
                  p: '0',
                  '& > textarea': {
                    padding: '6px 14px',
                    paddingBottom: '2em'
                  },
                  '&.Mui-disabled > textarea': {
                    color: t => t.palette.primary.main,
                    WebkitTextFillColor: t => t.palette.primary.main
                  }
                }
              }}
              value={value || ''}
              onBlur={onBlurHandler(onBlur)}
              onChange={e => onChange(e.target.value || null)}
            />
          )}
        />
        <Zoom in={mode === 'edit' && !isEditing}>
          <Box position="absolute" bottom="8px" right="8px" borderRadius="50%" bgcolor="rgba(255, 255, 255, 0.85)">
            <IconButton data-testid="document_details-description-edit_btn" size="medium" onClick={handleClickEdit}>
              <EditIcon />
            </IconButton>
          </Box>
        </Zoom>
      </Box>
      <Collapse in={isDirty}>
        <Stack direction="row" width="100%" py="10px" spacing={1} justifyContent="flex-end">
          <Button disabled={!isValid || !isDirty || isSubmitting} variant="contained" size="small" type="submit">
            Save
          </Button>
          <Button variant="outlined" size="small" onClick={handleCancelClick}>
            Cancel
          </Button>
        </Stack>
      </Collapse>
    </Box>
  );
};

export default UniversalDescription;
