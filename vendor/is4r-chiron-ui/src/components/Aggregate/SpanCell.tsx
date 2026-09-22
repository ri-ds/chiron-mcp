import { Tooltip } from "@mui/material";
import config from "../../config";
import {
  GridCell,
  GridCellProps,
  useGridApiContext,
} from "@mui/x-data-grid-pro";

//adapted from this solution for row spanning
//https://github.com/mui/mui-x/issues/207#issuecomment-1828317220

export function SpanCell(
  props: GridCellProps & { therows: object[]; height: string }
) {
  let style = {
    minWidth: props.width,
    maxWidth: props.width,
    minHeight: props.height,
    maxHeight: props.height === "auto" ? "none" : props.height,
    align: "left",
    ...props.style,
  };
  const apiRef = useGridApiContext();
  const row = apiRef.current.getRow(props.rowId);
  const cellValue = apiRef.current.getCellValue(
    props.rowId,
    props.column.field
  );
  let span = 1;
  let zIndex = 0;
  if (row.span && row.span[props.column.field]) {
    span = row.span[props.column.field] + 1;
    zIndex = 4;
    style = {
      ...style,
      minHeight: config.table.aggregateRowHeight * span,
      maxHeight: config.table.aggregateRowHeight * span,
      zIndex: zIndex,
      whiteSpace: "normal",
      wordWrap: "break-word",
    };
  }
  if (props.rowId == "") {
    style = {
      ...style,
      minHeight: 0,
      maxHeight: 0,
    };
  }
  return (
    <Tooltip title={cellValue} placement="right-start">
      <GridCell {...props} style={style} />
    </Tooltip>
  );
}
