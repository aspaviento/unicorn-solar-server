import * as React from 'react';

export interface IStatusButtonProps {
  apiUrl: string;
  className: string;
  text: string;
  description?: string;
  active?: boolean;
  preview?: React.ReactNode;
  callApi: (url: string) => Promise<void>;
}

export const StatusButton: React.FunctionComponent<IStatusButtonProps> = (props: IStatusButtonProps) => {
  return (
    <button
      className={`status-action ${props.className}${props.active ? ' active' : ''}`}
      onClick={() => props.callApi(props.apiUrl)}
      type="button">
      {props.preview}
      <span>{props.text}</span>
      {props.description && <small>{props.description}</small>}
    </button>
  );
};
