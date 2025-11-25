import React from 'react';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import Collapse from '@mui/material/Collapse';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Zoom from '@mui/material/Zoom';
import { Tiptap } from './TipTapEditor';

export type DescriptionFormFields = {
  description: string | null;
};

export type DescriptionFormSubmitHandler = SubmitHandler<DescriptionFormFields>;

interface DescriptionProps {
  descriptionText: string | null;
  onSubmitEdit: DescriptionFormSubmitHandler;
  maxLength?: number;
}

export const UniversalDescription: React.FC<DescriptionProps> = ({
  descriptionText,
  onSubmitEdit,
  maxLength = 200
}) => {
  const { handleSubmit, formState, setFocus, control, reset } = useForm<DescriptionFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: { description: descriptionText }
  });

  const mode = 'edit';

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

  const { isValid, isSubmitting, isDirty } = formState;

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmitEdit)}>
      <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
        Description
      </Typography>
      <Box position="relative">
        <Controller
          name="description"
          control={control}
          rules={{
            maxLength: {
              value: maxLength,
              message: `Description length should not exceed the limit of ${maxLength} characters.`
            }
          }}
          render={({ field: { onChange, value } }) => (
            <Box>
              <Tiptap descriptionText={descriptionText} value={value || ''} onChange={onChange} isEditing={isEditing} />
            </Box>
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
