import React from 'react';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';

import Box from '@mui/material/Box';
import Fade from '@mui/material/Fade';
import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';

import { useAuth } from '../../../contexts/auth/auth';

import MentionInput, { CommentInputValue } from '../CommentInput/CommentInput';

const avatarStyles = {
  width: 40,
  height: 40,
  marginTop: '8px !important',
  backgroundColor: (theme: { color: { blueGray: any } }) => theme.color.blueGray,
  fontSize: '14px',
  fontWeight: '600'
};

const actionButtonStyles = {
  width: '90px'
};

type NewCommentFormFields = {
  value: CommentInputValue;
};

interface User {
  id: number;
  first_name: string;
  last_name: string;
}

export type NewCommentFormSubmitHandler = SubmitHandler<NewCommentFormFields>;

export interface UniversalNewCommentFormProps {
  usersList?: User[];
  onSubmit: NewCommentFormSubmitHandler;
  onAction?: () => void;
  isDocumentModal?: boolean;
}

export interface UniversalNewCommentFormRef {
  resetForm: () => void;
}

export const UniversalNewCommentForm = React.forwardRef<UniversalNewCommentFormRef, UniversalNewCommentFormProps>(
  (props, ref) => {
    const { usersList, onSubmit, onAction, isDocumentModal } = props;
    const { user } = useAuth();

    if (!user) {
      throw new Error('UniversalNewCommentForm component requires user authentication');
    }

    const { handleSubmit, formState, control, reset } = useForm<NewCommentFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: { value: { plainValue: '', mentions: [] } }
    });

    React.useImperativeHandle(
      ref,
      () => ({
        resetForm: () => {
          reset();
        }
      }),
      [reset]
    );

    const handleCancelClick = () => {
      reset();
      onAction && onAction();
    };

    const convertIntoSuggestionIntems = React.useCallback(
      (user: User) => ({
        id: user.id,
        display: `${user.first_name} ${user.last_name}`
      }),
      []
    );

    const mentionSuggestions = React.useMemo(
      () => (usersList ? usersList.map(convertIntoSuggestionIntems) : []),
      [usersList, convertIntoSuggestionIntems]
    );

    const { errors, isValid, isSubmitting, isDirty } = formState;

    return (
      <Box component="form" onSubmit={handleSubmit(onSubmit)}>
        <Stack direction="row" spacing={2}>
          <Avatar
            data-testid="document-new_comment-avatar"
            sx={avatarStyles}
            alt={user.first_name + ' ' + user.last_name}
          >
            {user.first_name.charAt(0) + user.last_name.charAt(0)}
          </Avatar>
          <Controller
            name="value"
            control={control}
            rules={{
              validate: value => {
                if (!value.plainValue) return true;
                return (
                  value.plainValue.length <= 1000 ||
                  'Document comment length should not exceed the limit of 1000 characters.'
                );
              }
            }}
            render={({ field: { ref, value, onChange, ...field } }) => (
              <MentionInput
                {...field}
                value={value}
                ref={ref}
                onChange={onChange}
                suggestions={mentionSuggestions}
                placeholder="Add a comment…"
                helperText={errors.value?.message}
                error={!!errors.value}
              />
            )}
          />
        </Stack>
        <Box height="52px">
          <Fade in={isDirty || isDocumentModal}>
            <Stack
              direction="row"
              width="100%"
              height="52px"
              py="10px"
              spacing={1}
              alignItems="center"
              justifyContent="flex-end"
            >
              <Button
                sx={actionButtonStyles}
                disabled={!isValid || !isDirty || isSubmitting}
                variant="contained"
                size="small"
                type="submit"
              >
                Save
              </Button>
              <Button sx={actionButtonStyles} variant="outlined" size="small" onClick={handleCancelClick}>
                Cancel
              </Button>
            </Stack>
          </Fade>
        </Box>
      </Box>
    );
  }
);

UniversalNewCommentForm.displayName = 'UniversalNewCommentForm';

export default UniversalNewCommentForm;
