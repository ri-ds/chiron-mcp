import {
  Paper,
  Box,
  CircularProgress,
  IconButton,
  Alert,
  Typography,
} from "@mui/material";

import { DataGridPro, GridCellParams } from "@mui/x-data-grid-pro";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { SpanCell } from "./SpanCell";
import EditAggTable from "./EditTable";
import { grey } from "@mui/material/colors";
import EmptyAggregateTable from "./EmptyAggregate";
import {
  calcHeaderColWidth,
  colGroupRecursor,
  returnHeaderColumnComponent,
  returnHeaderGroupComponent,
} from "./TableDataFormatter";
import {
  AddCircleOutline,
  RemoveCircle as RemoveIcon,
} from "@mui/icons-material";
import {
  AggTableItem,
  applyTransformation,
  aggItemsForEditing,
} from "../../store/aggregateSlice";
import config from "../../config";

export default function AggregateTable() {
  const dispatch = useAppDispatch();
  const columns = useAppSelector((state) => state.aggregate.columns);
  const rows = useAppSelector((state) => state.aggregate.rows);
  const aggStatus = useAppSelector((state) => state.aggregate.aggStatus);
  const aggregateData = useAppSelector((state) => state.aggregate.dataset);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const leafDepth = columns.length;

  if (aggregateData && aggregateData.data?.length == 0) {
    return (
      <Box>
        <Alert severity="info">
          {" "}
          <Typography>Aggregate data empty for selected concepts.</Typography>
          <Typography>
            {" "}
            <b>Rows :</b> {rows.map((r) => r.name).join(", ")} <b>Columns :</b>{" "}
            {columns.map((c) => c.name).join(", ")}
          </Typography>
        </Alert>
      </Box>
    );
  }

  const columnMetaGroups =
    aggregateData?.columnMetaGroups != undefined &&
    aggregateData.columnMetaGroups.length > 0
      ? colGroupRecursor(
          aggregateData?.columnMetaGroups[0],
          0,
          leafDepth,
          columns,
          dispatch,
          dataset ? dataset : ""
        )
      : [];

  const borderRadius = 20;
  //should be GridPinnedRowsProp but causing type error with mui pro v7 upgrade
  const pinnedVals: any = {
    top:
      aggregateData?.data && Object.keys(aggregateData.data)
        ? [aggregateData?.data[0]]
        : [],
  };

  return (
    <>
      <EditAggTable />
      {aggStatus != "loading" ? (
        <>
          <Box sx={{ p: 2 }}>
            {columns.length == 0 && rows.length == 0 ? (
              <EmptyAggregateTable></EmptyAggregateTable>
            ) : (
              <>
                {aggregateData != undefined &&
                aggregateData.columns != undefined &&
                aggregateData.data != undefined &&
                aggregateData.columnGroups != undefined ? (
                  <Paper
                    sx={{
                      width: "100%",
                      height: "80vh",
                      overflow: "scroll",
                      "& .header-group": {
                        justifyContent: "flex-start !important",
                        pl: "5px ",
                        pr: "10px ",
                        fontWeight:
                          "var(--unstable_DataGrid-headWeight) !important",
                        borderRight: "1px solid #d3d3d3 !important",
                      },
                      "& .tab-top": {
                        pt: "10px !important",
                        paddingBottom: 3,
                        borderTopRightRadius: borderRadius,
                        borderTopLeftRadius: borderRadius,
                        pl: 2,
                        pb: "10px !important",
                        mt: 1,
                      },
                      "& .tab-left": {
                        paddingTop: 1,
                        pl: 2,
                        borderBottomLeftRadius: borderRadius,
                        borderTopLeftRadius: borderRadius,
                      },
                      "& .header-row": {
                        justifyContent: "flex-start !important",
                        fontWeight: 500,
                        fontSize: ".8rem",
                      },
                      "& .MuiDataGrid-columnHeaders": {
                        borderBottom: columns.length > 0 ? 0 : 0,
                      },
                      "& .MuiDataGrid-columnHeader--withRightBorder": {
                        borderRight: 0.1,
                        borderColor: grey[400],
                        justifyContent: "center",
                      },
                      "& div div div div >.MuiDataGrid-cell": {
                        borderBottom: 0,
                      },
                      "& .blue-col-bg-0": {
                        backgroundColor:
                          config.table.aggHeaderColor[50] + " !important",
                      },
                      "& .blue-col-bg-1": {
                        backgroundColor:
                          config.table.aggHeaderColor[100] + " !important",
                      },
                      "& .blue-col-bg-2": {
                        backgroundColor:
                          config.table.aggHeaderColor[200] + " !important",
                      },
                      "& .grey-cell": {
                        backgroundColor: grey[100],
                      },
                      "& .base-cell": {
                        justifyContent: "flex-end",
                        borderRight: 1,
                        borderBottom: "0px solid #d3d3d3 !important",
                        borderColor: grey[300],
                      },
                      "& .MuiDataGrid-columnHeader--emptyGroup": {
                        borderWidth: "0px !important",
                      },
                      "& .iconmouse": {
                        position: "absolute",
                        top: 0,
                        right: 0,
                        visibility: "hidden",
                        backgroundColor: grey[100],
                        borderRadius: 10,
                      },
                      "& .header-group:hover .iconmouse": {
                        visibility: "visible",
                      },
                      "& .MuiDataGrid-cell.MuiDataGrid-cellEmpty": {
                        borderTop: "0px",
                      },
                      "& .MuiDataGrid-filler--pinnedLeft": {
                        borderRight: "0px",
                      },
                    }}
                  >
                    <DataGridPro
                      sx={{
                        minHeight: 700,
                        pl: 1,
                        pt: 1,
                      }}
                      //@ts-expect-error: doesnt like cell with additional slotprops
                      slots={{ cell: SpanCell }}
                      slotProps={{
                        //@ts-expect-error: doesnt like cell with additional slotprops
                        cell: { therows: rows },
                      }}
                      disableColumnFilter={true}
                      disableColumnSelector={true}
                      disableColumnMenu={true}
                      showColumnVerticalBorder={true}
                      //@ts-expect-error: datagridpro doesnt like this external setting
                      experimentalFeatures={{ columnGrouping: true }}
                      columnGroupingModel={columnMetaGroups.concat(
                        aggregateData.columnGroups?.map((cg) => {
                          return {
                            ...cg,
                            renderHeaderGroup: () =>
                              returnHeaderGroupComponent(
                                cg,
                                columns,
                                dispatch,
                                dataset ? dataset : ""
                              ),
                          };
                        })
                      )}
                      columns={aggregateData.columns?.map((k) => {
                        return {
                          ...k,
                          disableColumnMenu: true,
                          filterable: false,
                          hideSortIcons: true,
                          sortable: false,
                          align: "center",
                          headerClassName: (d) => {
                            if (d.colDef.headerName == "") {
                              return "MuiDataGrid-columnHeader--emptyGroup";
                            }
                            if (
                              columns.find((c) => c.entryId == d.field)
                                ?.entryId ||
                              (rows.length > 0 &&
                                (rows[rows.length - 1].entryId == d.field) ==
                                  true)
                            ) {
                              return "header-group tab-left blue-col-bg-0";
                            }
                            return "header-row header-group blue-col-bg-0";
                          },
                          minWidth: calcHeaderColWidth(k, rows, columns),
                          renderCell: (
                            params: GridCellParams<AggTableItem>
                          ) => {
                            if (
                              rows.find((r) => r.name == params.value) !=
                              undefined
                            ) {
                              const cellText: string = params.value
                                ? params.value.toString()
                                : "";
                              return (
                                <Box sx={{ textAlign: "left !important" }}>
                                  {cellText}
                                  <Box className="iconmouse">
                                    <IconButton
                                      onClick={() =>
                                        dispatch(
                                          applyTransformation({
                                            transformation: {
                                              type: "delete_entry",
                                              entry_id: params.field,
                                            },
                                            dataset: dataset ? dataset : "",
                                          })
                                        )
                                      }
                                    >
                                      <RemoveIcon
                                        color="error"
                                        fontSize="small"
                                      />
                                    </IconButton>
                                    <IconButton
                                      onClick={() =>
                                        dispatch(aggItemsForEditing("Rows"))
                                      }
                                    >
                                      <AddCircleOutline fontSize="small" />
                                    </IconButton>
                                  </Box>
                                </Box>
                              );
                            }
                            if (params.value == undefined) {
                              if (params.row.id != "") {
                                if (rows.length == 0) {
                                  return (
                                    <Box sx={{ backgroundColor: grey[100] }}>
                                      Add Rows
                                      <IconButton
                                        onClick={() =>
                                          dispatch(aggItemsForEditing("Rows"))
                                        }
                                      >
                                        <AddCircleOutline fontSize="small" />
                                      </IconButton>
                                    </Box>
                                  );
                                }
                                if (columns.length == 0) {
                                  return (
                                    <Box pl={1} pt={1}>
                                      Add Columns
                                      <IconButton
                                        onClick={() =>
                                          dispatch(
                                            aggItemsForEditing("Columns")
                                          )
                                        }
                                      >
                                        <AddCircleOutline fontSize="small" />
                                      </IconButton>
                                    </Box>
                                  );
                                }
                                return;
                              }
                            }

                            return <>{params.value}</>;
                          },
                          renderHeader: () =>
                            returnHeaderColumnComponent(
                              k,
                              rows,
                              columns,
                              dispatch,
                              dataset ? dataset : ""
                            ),
                          cellClassName: (
                            params: GridCellParams<AggTableItem>
                          ) => {
                            const bgColorChoices = 2;
                            if (params.value == undefined) {
                              return "grey-cell base-cell";
                            }

                            let classString = "header-row";
                            //check if this cell is in the header row (i.e. the cell value is identical to a row name)
                            const rowIdx: number = Math.min(
                              rows.findIndex((r) => r.name == params.value),
                              bgColorChoices
                            );

                            //check cell background class number to apply to
                            const dataRowIdx: number = Math.min(
                              [...rows]
                                .reverse()
                                .findIndex((r) => r.entryId == k.field),
                              bgColorChoices
                            );
                            if (rowIdx > -1) {
                              classString = "header-group tab-top";
                            }

                            if (dataRowIdx > -1) {
                              return `${classString} blue-col-bg-${dataRowIdx} base-cell`;
                            }

                            const dataColIdx: number = Math.min(
                              columns.findIndex((c) => c.entryId == k.field),
                              bgColorChoices
                            );
                            if (dataColIdx > -1) {
                              return "blue-col-bg-0 base-cell";
                            }
                            return "base-cell";
                          },
                        };
                      })}
                      columnHeaderHeight={columns.length > 0 ? 70 : 20}
                      rows={aggregateData.data}
                      initialState={{
                        pinnedColumns: {
                          left:
                            rows.length > 0
                              ? rows.map((r) => r.entryId)
                              : [columns[columns.length - 1].entryId],
                        },
                      }}
                      pinnedRows={pinnedVals}
                      getRowHeight={(row) => {
                        //make sure label row height always stretches
                        if (
                          rows.length > 0 &&
                          row.id == rows.map((r) => r.entryId).join(",")
                        ) {
                          return "auto";
                        }
                        //this makes empty row height 0
                        if (row.id == "") {
                          return "auto";
                        } else {
                          return config.table.aggregateRowHeight;
                        }
                      }}
                      //we can decide whether to virtualize
                      columnBufferPx={100}
                      rowBufferPx={1000}
                      //disableVirtualization
                    ></DataGridPro>
                  </Paper>
                ) : (
                  <CircularProgress size={50} />
                )}
              </>
            )}
          </Box>
        </>
      ) : null}
    </>
  );
}
