import React from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Box
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { apiService } from '../services/api';

const SummaryCard = ({ title, value, icon }) => (
  <Card>
    <CardContent>
      <Box display="flex" alignItems="center" gap={2}>
        {icon}
        <Box>
          <Typography variant="h6" color="textSecondary">{title}</Typography>
          <Typography variant="h4">{value}</Typography>
        </Box>
      </Box>
    </CardContent>
  </Card>
);

const StatsPage = () => {
  const queryClient = useQueryClient();

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useQuery('collectionSummary', apiService.getCollectionSummary, {
    refetchInterval: 60000,
  });

  const {
    data: duplicates,
    isLoading: duplicatesLoading,
    error: duplicatesError,
  } = useQuery('duplicates', apiService.getDuplicates, {
    refetchInterval: 60000,
  });

  const maintenanceMutation = useMutation(apiService.runMaintenance, {
    onSuccess: () => {
      queryClient.invalidateQueries('collectionSummary');
      queryClient.invalidateQueries('duplicates');
    },
  });

  const handleRunMaintenance = () => {
    maintenanceMutation.mutate();
  };

  if (summaryLoading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (summaryError) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">Failed to load collection summary: {summaryError.message}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          System Dashboard
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<RefreshIcon />}
            onClick={() => {
              queryClient.invalidateQueries('collectionSummary');
              queryClient.invalidateQueries('duplicates');
            }}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            color="secondary"
            startIcon={<FactCheckIcon />}
            onClick={handleRunMaintenance}
            disabled={maintenanceMutation.isLoading}
          >
            {maintenanceMutation.isLoading ? 'Running…' : 'Run Maintenance'}
          </Button>
        </Box>
      </Box>

      {maintenanceMutation.isSuccess && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Maintenance completed. Publication updates: {maintenanceMutation.data.update_report.publication_updates.length},
          Invalid files: {maintenanceMutation.data.quality_report.invalid_files.length}
        </Alert>
      )}

      {maintenanceMutation.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to run maintenance.
        </Alert>
      )}

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="Total Papers"
            value={summary?.total_papers?.toLocaleString() ?? '0'}
            icon={<ContentCopyIcon color="primary" fontSize="large" />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="Published"
            value={summary?.by_type?.published ?? 0}
            icon={<FactCheckIcon color="success" fontSize="large" />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="Recent Additions"
            value={summary?.recent_additions ?? 0}
            icon={<RefreshIcon color="secondary" fontSize="large" />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="Duplicate Groups"
            value={summary?.total_duplicates ?? 0}
            icon={<ContentCopyIcon color="warning" fontSize="large" />}
          />
        </Grid>
      </Grid>

      <Typography variant="h5" gutterBottom>
        Duplicate Candidates
      </Typography>
      {duplicatesError && <Alert severity="error">Failed to load duplicates: {duplicatesError.message}</Alert>}
      {duplicatesLoading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} sx={{ mb: 4 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Paper 1</TableCell>
                <TableCell>Paper 2</TableCell>
                <TableCell>Similarity</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(duplicates?.duplicates ?? []).map((item, index) => (
                <TableRow key={index}>
                  <TableCell>{item.paper1?.title || item.paper1?.file_path}</TableCell>
                  <TableCell>{item.paper2?.title || item.paper2?.file_path}</TableCell>
                  <TableCell>{(item.similarity * 100).toFixed(1)}%</TableCell>
                </TableRow>
              ))}
              {(duplicates?.duplicates ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} align="center">
                    No duplicates detected.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Container>
  );
};

export default StatsPage;
