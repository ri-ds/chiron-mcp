import {
  GridColDef,
  GridColumnGroup,
  GridColumnGroupingModel,
} from "@mui/x-data-grid";

import {
  AggTableItem,
  applyTransformation,
  aggItemsForEditing,
} from "../../store/aggregateSlice";
import { Box, IconButton, Tooltip } from "@mui/material";
import {
  AddCircleOutline,
  RemoveCircle as RemoveIcon,
} from "@mui/icons-material";
import { AppDispatch } from "../../store";

// Adds renderHeaderGroup attribute to column groups
export function colGroupRecursor(
  cc: GridColumnGroup,
  level: number,
  leafDepth: number,
  columns: AggTableItem[],
  dispatch: AppDispatch,
  dataset: string
): GridColumnGroupingModel {
  if (leafDepth < 2) {
    return [];
  }
  if (level >= leafDepth - 2) {
    return [
      {
        ...cc,
        renderHeaderGroup: () =>
          returnHeaderGroupComponent(cc, columns, dispatch, dataset),
      },
    ];
  } else {
    const ccChildren = cc?.children;
    const retObj = {
      ...cc,
      renderHeaderGroup: () =>
        returnHeaderGroupComponent(cc, columns, dispatch, dataset),
      // @ts-expect-error/the GridColumnGroup/GridLeafNode return type error
      children: colGroupRecursor(
        ccChildren[0],
        level + 1,
        leafDepth,
        columns,
        dispatch
      ),
    };
    return [retObj];
  }
}

// Returned HeaderGroup component
export function returnHeaderGroupComponent(
  cg: GridColumnGroup,
  columns: AggTableItem[],
  dispatch: AppDispatch,
  dataset: string
) {
  return (
    <Tooltip title={cg.headerName} placement="left-start">
      <Box
        sx={{ whiteSpace: "wrap" }}
        textAlign={"center"}
        justifyContent={"center"}
      >
        <p>
          {cg.headerName}
          {columns.find((c) => c.entryId == cg.groupId) != undefined ? (
            <Box className="iconmouse">
              <IconButton
                onClick={() =>
                  dispatch(
                    applyTransformation({
                      dataset: dataset ? dataset : "",
                      transformation: {
                        type: "delete_entry",
                        entry_id: cg.groupId,
                      },
                    })
                  )
                }
              >
                <RemoveIcon color="error" fontSize="small" />
              </IconButton>
              <IconButton
                onClick={() => dispatch(aggItemsForEditing("Columns"))}
              >
                <AddCircleOutline fontSize="small" />
              </IconButton>
            </Box>
          ) : null}
        </p>
      </Box>
    </Tooltip>
  );
}

// Returned Header column component, including remove button if in row or base col
export function returnHeaderColumnComponent(
  k: GridColDef,
  rows: AggTableItem[],
  columns: AggTableItem[],
  dispatch: AppDispatch,
  dataset: string
) {
  let itemType: string | undefined = undefined;
  if (rows.length > 0 && (rows[rows.length - 1].entryId == k.field) == true) {
    itemType = "Columns";
  }
  const colVal = columns.find((c) => c.name == k.headerName)?.entryId;
  if (colVal) {
    itemType = "Columns";
  }
  return (
    <Tooltip title={k.headerName} placement="left-start">
      <Box sx={{ whiteSpace: "wrap", lineHeight: "20px" }} textAlign={"center"}>
        {k.headerName}
        {itemType != undefined ? (
          <Box className="iconmouse">
            <IconButton
              onClick={() =>
                dispatch(
                  applyTransformation({
                    dataset: dataset ? dataset : "",
                    transformation: {
                      type: "delete_entry",
                      entry_id: colVal ? colVal : "",
                    },
                  })
                )
              }
            >
              <RemoveIcon color="error" fontSize="small" />
            </IconButton>
            <IconButton onClick={() => dispatch(aggItemsForEditing("Columns"))}>
              <AddCircleOutline fontSize="small" />
            </IconButton>
          </Box>
        ) : null}
      </Box>
    </Tooltip>
  );
}

export function calcHeaderColWidth(
  k: GridColDef,
  rows: AggTableItem[],
  columns: AggTableItem[]
) {
  if (k.headerName == undefined) {
    return 170;
  }
  let minWidth = 110;
  let entryLength = k.headerName.length;
  const inRows = rows.find((r) => r.entryId == k.field);
  if (inRows) {
    minWidth = 110;
    entryLength = inRows.name.length;
  }
  const inCols = columns.find((c) => c.entryId == k.field);
  if (inCols != undefined) {
    minWidth = 110;
  }
  return Math.max((entryLength / 15) * 100, minWidth);
}

/* 
HELPER FUNCTIONS FOR HEADER GROUP DATA FORMATTING
Need to take in the string formatted sets as keys of dictionary data from API, make it into an acceptable format
for flexible GridColDef columns Grouping
 */

/* format the list or string passed from python*/
function formatLabelValue(value: string | boolean | (string | boolean)[]) {
  if (typeof value == "string") {
    return [value];
  }
  if (typeof value == "boolean") {
    return [value.toString()];
  }
  return value.map((v) => {
    return typeof v == "boolean" ? v.toString() : v;
  });
}
//Column group tree creation
function createGroup(
  gData: string[][],
  level: number,
  leafDepth: number,
  prevGroupIdStr: string = ""
): GridColumnGroupingModel {
  //if fewer than 2 selected columns, we don't need extra header rows
  if (leafDepth < 2) {
    return [];
  }

  //Inner recursive function so we can return either coldef objects or group objects
  function createInnerGroup(
    gData: string[][],
    level: number,
    prevGroupIdStr: string = ""
  ): GridColumnGroupingModel | { field: string }[] {
    //add in column mapping for leafs
    if (level >= leafDepth - 1) {
      return gData.map(function (g) {
        return { field: g.toString() };
      });
    }

    //Get unique number of subcolumns at this level,
    const uniqueLevel = [
      ...new Set(
        gData.map(function (g) {
          return g[level];
        })
      ),
    ];

    //Recurse on each unique subcolumn
    //passing in only the data that matches the subcolumn value
    const groupObj = uniqueLevel.map(function (ul) {
      const groupIdStr = prevGroupIdStr + " " + ul;
      return {
        groupId: groupIdStr,
        headerName: ul,
        description: "",
        headerClassName: `header-group blue-col-bg-${Math.min(leafDepth - 1 - level, 2)}`,
        children: createInnerGroup(
          gData.filter(function (g) {
            return g[level] == ul;
          }),
          level + 1,
          (prevGroupIdStr = groupIdStr)
        ),
      };
    });
    return groupObj;
  } //createInnerGroup

  //creates initial set of unique subcolumns at this level
  const uniqueLevel = [
    ...new Set(
      gData.map(function (g) {
        return g[level];
      })
    ),
  ];
  //initial call to inner function
  const groupObj = uniqueLevel.map(function (ul) {
    const groupIdStr = prevGroupIdStr + " " + ul;
    return {
      groupId: groupIdStr,
      headerName: ul,
      description: "",
      headerClassName: `header-group blue-col-bg-${Math.min(leafDepth - 1 - level, 2)}`,
      children: createInnerGroup(
        gData.filter(function (g) {
          return g[level] == ul;
        }),
        level + 1,
        (prevGroupIdStr = groupIdStr)
      ),
    };
  });
  return groupObj;
} //createGroup

/*createColumnGroup */
/* creates additional column group for selected columns only, with last selected column as leaf*/
function createColumnGroup(
  level: number,
  columns: AggTableItem[],
  rows: AggTableItem[],
  leafDepth: number
): GridColumnGroupingModel {
  if (leafDepth < 2) {
    return [];
  }
  if (level >= leafDepth - 2) {
    const retobj = [
      {
        groupId: columns[level].entryId,
        headerName: columns[level].name,
        headerClassName: `header-group blue-col-bg-${Math.min(leafDepth - 1 - level, 2)} tab-left`,
        description: "",
        children: [
          {
            field:
              rows.length >= 1
                ? rows[rows.length - 1].entryId
                : columns.length >= 1
                  ? columns[columns.length - 1].entryId
                  : "column-levels-label",
          },
        ],
      },
    ];

    return retobj;
  } else {
    return [
      {
        groupId: columns[level].entryId,
        headerName: columns[level].name,
        headerClassName: `header-group blue-col-bg-${Math.min(leafDepth - 1 - level, 2)} tab-left`,
        description: "",
        children: createColumnGroup(level + 1, columns, rows, leafDepth),
      },
    ];
  }
} //CreateColumnGroup

/*
 Function to parse returned data and format it for our aggregate/analysis table
 transposes the data, then constructs a gridcolumngrouping n-tree type object along with row and columns
 @params
 dataset : api response of run_analysis
 rows : selected rows,
 columns selected columns
 @returns :
 {
   data: list of row objects, key value pairs, key corresponding to column field id, pair corresponding to cell value.
    columns: list of columns (lowest row of header columns, list of field ids, display values )
    columnGroups: constructed tree, where leafs correspond to column field ids,
    columnMetaGroups: the additional column group for the selected columns, each has one child, columns.length < 2,
 }
 */
export function cleanDataSet(
  dataset: {
    columns: (string | boolean)[];
    index: (string | boolean)[];
    data: number[][];
  },
  rows: AggTableItem[],
  columns: AggTableItem[]
) {
  //return if empty or {}
  if (dataset == null) {
    return undefined;
  }

  // define return vars
  const formattedColumns: GridColDef[] = [];
  const leafDepth = columns.length;
  const newData: {
    [key: string]: {
      [key: string]: string | number | { [key: string]: number };
    };
  } = {};

  /* set up  metadata columns */
  //add columns for the selected rows
  if (rows.length > 0) {
    rows.forEach(function (r, i) {
      formattedColumns.push({
        field: r.entryId,
        headerName:
          columns.length > 0 && rows.length - 1 == i
            ? columns[columns.length - 1].name
            : "",
        hideable: true,
        headerClassName:
          rows.length - 1 == i ? "header-group " : "header-group",
      });
    });
  } else {
    //add a single column for the selected columns, and leave it empty if there are no selected
    formattedColumns.push({
      field:
        columns.length >= 1
          ? columns[columns.length - 1].entryId
          : "column-levels-label",
      headerName: columns.length >= 1 ? columns[columns.length - 1].name : "",
      hideable: true,
      headerClassName: "header-group",
    });
  }

  //handle case when data is not null, but an empty object, we handle this differently in ui
  if (Object.keys(dataset).length == 0) {
    return {
      data: [],
      columns: undefined,
      columnGroups: undefined,
      columnMetaGroups: undefined,
    };
  }

  // build transpose keys with first row of data as reference
  //if subsequent rows have different column keys then unknown behavior, but i dont think that happens
  const dataKeys = dataset.columns;
  dataset.index.forEach((k) => {
    newData[formatLabelValue(k).toString()] = {};
  });

  //object to track the number of rows an aggregated cell should span
  //key is the selected row concept's entryid
  //spanrow is the row that contains the cell we are tracking the span for

  const rowSpanTracker: {
    [key: string]: {
      spanRow: {
        [key: string]: string | number | { [key: string]: number };
      };
      spanCount: number;
    };
  } = {};

  rows.forEach(function (r) {
    //@ts-expect-error: set initially to undefined
    rowSpanTracker[r.entryId] = undefined;
  });
  //transpose data, add data columns to columns set
  dataKeys.forEach(function (k, c_i) {
    const parsedColumn = formatLabelValue(k);
    const parsedColumnString = parsedColumn.toString();
    formattedColumns.push({
      field: parsedColumnString,
      headerName: parsedColumn[leafDepth - 1],
      headerClassName: "header-row header-group",
    });

    dataset.index.forEach((rk, r_i) => {
      const rowK = formatLabelValue(rk);
      const rowKString = rowK.toString();
      newData[rowKString][parsedColumnString] = dataset.data[r_i][c_i];
      newData[rowKString].span = {};
      rows.forEach(function (r, i) {
        newData[rowKString][r.entryId] = rowK[i];
        if (i < rows.length - 1) {
          if (rowSpanTracker[r.entryId] == undefined) {
            rowSpanTracker[r.entryId] = {
              spanRow: newData[rowKString],
              spanCount: 0,
            };
          } else {
            //if the label cell is different, then we set the active cell
            //then we set the new row/cell to calculate
            //has to be nested because we are tracking multiple cell spans in one row.
            if (rowSpanTracker[r.entryId].spanRow[r.entryId] != rowK[i]) {
              if (rowSpanTracker[r.entryId].spanCount > 0) {
                //@ts-expect-error: handle issue with span typing
                rowSpanTracker[r.entryId].spanRow.span[r.entryId] =
                  rowSpanTracker[r.entryId].spanCount;
              }
              rowSpanTracker[r.entryId] = {
                spanRow: newData[rowKString],
                spanCount: 0,
              };
            } else {
              rowSpanTracker[r.entryId].spanCount += 1;
            }
          }
        }
      });
      newData[rowKString].id = parsedColumnString + rowKString;
    });
  });

  //set span for last group
  rows.forEach(function (r, i) {
    if (i < rows.length - 1) {
      if (
        rowSpanTracker[r.entryId] &&
        rowSpanTracker[r.entryId].spanCount > 0
      ) {
        //@ts-expect-error: handle issue with span typing
        rowSpanTracker[r.entryId].spanRow.span[r.entryId] =
          rowSpanTracker[r.entryId].spanCount;
      }
    }
  });

  const selectedRowData: {
    [key: string]: string | number | { [key: string]: number };
  }[] = [];

  selectedRowData.push({ id: rows.map((r) => r.entryId).join() });

  rows.forEach(function (r) {
    selectedRowData[0][r.entryId] = r.name;
  });
  const retobj = {
    data: selectedRowData.concat(Object.values(newData)),
    columns: formattedColumns,
    columnGroups: createGroup(dataKeys.map(formatLabelValue), 0, leafDepth),
    columnMetaGroups: createColumnGroup(0, columns, rows, leafDepth),
  };

  return retobj;
} //cleanDataSet
