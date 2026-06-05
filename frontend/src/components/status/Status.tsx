import * as React from 'react';
import { RGB } from '../../models';
import { content } from '../../content';

export interface IStatusProps {
  status: string | null;
  rgb: RGB | null;
  label: string;
  description: string;
  preview: React.ReactNode;
}

export const Status: React.FunctionComponent<IStatusProps> = (props: IStatusProps) => {
  const backgroundColor = props.rgb ? `rgb(${props.rgb.red}, ${props.rgb.green}, ${props.rgb.blue})` : undefined;

	return (
    <section className="status-panel" aria-live="polite">
      <div className="status-led" style={{ backgroundColor }}>
        {props.preview}
      </div>
      <div className="status-copy">
        <span className="status-kicker">{content.appName}</span>
        <h1>{props.label}</h1>
        <p>{props.description}</p>
      </div>
    </section>
	);
};
