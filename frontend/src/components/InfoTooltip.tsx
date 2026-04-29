type Props = {
  content: string;
};

function InfoTooltip({ content }: Props) {
  return (
    <span className="group/tooltip relative inline-flex items-center">
      <button
        type="button"
        tabIndex={0}
        aria-label="More information"
        className="ui-tooltip-trigger"
      >
        i
      </button>
      <span className="ui-tooltip-panel">
        {content}
      </span>
    </span>
  );
}

export default InfoTooltip;
