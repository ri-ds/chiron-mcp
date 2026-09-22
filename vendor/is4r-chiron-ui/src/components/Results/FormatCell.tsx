import { Link, Typography } from "@mui/material";

type ResultCellProps = {
  item: any;
};

export default function FormatCell({ item }: ResultCellProps) {
  if (item === null) {
    return (
      <Typography variant="caption" fontStyle="italic" color="GrayText">
        null
      </Typography>
    );
  }

  switch (typeof item) {
    case "boolean":
      return item ? "True" : "False";
    case "object":
      if (item.link) {
        return (
          <Link underline="none" target="_blank" href={item.link}>
            {item.value}
          </Link>
        );
      } else if (Array.isArray(item)) {
        return item.join("; ");
      }
      return "object";
    case "string":
    default:
      return item;
  }
}
