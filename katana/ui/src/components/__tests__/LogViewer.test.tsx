import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import LogViewer from '../LogViewer'; // Adjust path if LogViewer is elsewhere

// Mock global fetch
global.fetch = jest.fn();

const mockLogEntry = (id: number, level: string, message: string, module: string = 'test-module', timestamp?: string) => ({
  timestamp: timestamp || new Date(Date.now() - id * 1000).toISOString(), // Ensure unique, descending timestamps
  level,
  module: `${module}-${id}`,
  message: `${message} ${id}`,
});

// Helper to mock fetch responses
const mockFetchResponse = (data: any, ok: boolean = true, status: number = 200) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok,
    status,
    json: async () => data,
    statusText: ok ? 'OK' : 'Error',
  } as Response);
};

const mockFetchError = (error: Error) => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(error);
};


describe('LogViewer Component', () => {
  beforeEach(() => {
    // Reset fetch mock before each test
    (global.fetch as jest.Mock).mockClear();
    // Reset initialLoadDone for components that might rely on it for conditional rendering
    // This is tricky as component internal state isn't easily reset externally without remounting.
    // Keying the component or full remount per test (`render` does this) is typical.
  });

  test('renders loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() =>
      new Promise(() => {}) // Simulate pending promise, never resolves
    );
    render(<LogViewer />);
    expect(screen.getByText(/loading logs.../i)).toBeInTheDocument();
  });

  test('renders log entries after successful fetch', async () => {
    const logs = [
      mockLogEntry(1, 'INFO', 'Info message'),
      mockLogEntry(2, 'ERROR', 'Error message'),
    ];
    mockFetchResponse(logs);
    render(<LogViewer />);

    // Wait for the first log entry's message to appear
    await waitFor(() => {
      expect(screen.getByText(/info message 1/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/error message 2/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading logs.../i)).not.toBeInTheDocument();
  });

  test('displays error message on fetch failure (network error)', async () => {
    mockFetchError(new Error('Network Error'));
    render(<LogViewer />);
    await waitFor(() => expect(screen.getByText(/error fetching logs: network error/i)).toBeInTheDocument());
  });

  test('displays error message on fetch failure (API error response)', async () => {
    mockFetchResponse({ detail: "Internal Server Problem" }, false, 500);
    render(<LogViewer />);
    await waitFor(() => expect(screen.getByText(/error fetching logs: internal server problem/i)).toBeInTheDocument());
  });


  test('handles empty log response', async () => {
    mockFetchResponse([]);
    render(<LogViewer />);
    await waitFor(() => expect(screen.getByText(/no log entries found./i)).toBeInTheDocument());
  });

  test('pagination: "Load More" button fetches next page', async () => {
    const initialLogs = Array.from({ length: 50 }, (_, i) => mockLogEntry(i + 1, 'INFO', 'Initial log'));
    const nextLogs = [mockLogEntry(51, 'DEBUG', 'Next page log')];

    // Mock page 1
    (global.fetch as jest.Mock).mockImplementationOnce(async (url: string) => {
        expect(url).toContain('/api/logs?page=1&limit=50');
        return Promise.resolve({ ok: true, json: async () => initialLogs } as Response);
    });

    render(<LogViewer />);
    await waitFor(() => expect(screen.getByText(/initial log 50/i)).toBeInTheDocument(), { timeout: 2000 });

    // Mock page 2
    (global.fetch as jest.Mock).mockImplementationOnce(async (url: string) => {
        expect(url).toContain('/api/logs?page=2&limit=50');
        return Promise.resolve({ ok: true, json: async () => nextLogs } as Response);
    });

    const loadMoreButton = screen.getByRole('button', { name: /load more/i });
    fireEvent.click(loadMoreButton);

    await waitFor(() => expect(screen.getByText(/next page log 51/i)).toBeInTheDocument(), { timeout: 2000 });
    expect(global.fetch).toHaveBeenCalledTimes(2);
    // Check specific calls (simplified, full URL check in mockImplementation)
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('page=1');
    expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('page=2');
  });

  test('disables "Load More" if no more logs (fewer than limit returned)', async () => {
    const logs = [mockLogEntry(1, 'INFO', 'Log entry')]; // Fewer than LOGS_PER_PAGE
    mockFetchResponse(logs);
    render(<LogViewer />);

    await waitFor(() => expect(screen.getByText(/log entry 1/i)).toBeInTheDocument());
    // Check for "No more logs to load" text
    await waitFor(() => expect(screen.getByText(/no more logs to load/i)).toBeInTheDocument());
    // Check if button is present and disabled
    const loadMoreButton = screen.queryByRole('button', { name: /load more/i });
    expect(loadMoreButton).toBeNull(); // Or expect it to be disabled if it's always rendered
  });


  test('filtering by level updates API call and logs', async () => {
    // Initial load (all levels)
    mockFetchResponse([mockLogEntry(1, 'INFO', 'Info message for level test')]);

    render(<LogViewer />);
    await waitFor(() => expect(screen.getByText(/info message for level test 1/i)).toBeInTheDocument());

    // Mock response for ERROR level filter
    (global.fetch as jest.Mock).mockImplementationOnce(async (url: string) => {
      expect(url).toContain('/api/logs?page=1&limit=50&level=ERROR');
      return Promise.resolve({ ok: true, json: async () => [mockLogEntry(2, 'ERROR', 'Error message after filter')] } as Response);
    });

    const levelSelect = screen.getByLabelText(/log level/i);
    fireEvent.change(levelSelect, { target: { value: 'ERROR' } });

    await waitFor(() => expect(screen.getByText(/error message after filter 2/i)).toBeInTheDocument());
    // First call on mount, second on filter change
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('level=ERROR');
  });

  test('searching by term updates API call and logs', async () => {
    // Initial load
    mockFetchResponse([mockLogEntry(1, 'INFO', 'Message with apple')]);

    render(<LogViewer />);
    await waitFor(() => expect(screen.getByText(/message with apple 1/i)).toBeInTheDocument());

    // Mock response for search term
     (global.fetch as jest.Mock).mockImplementationOnce(async (url: string) => {
      expect(url).toContain('/api/logs?page=1&limit=50&search=banana');
      return Promise.resolve({ ok: true, json: async () => [mockLogEntry(2, 'INFO', 'Message with banana search result')] } as Response);
    });

    const searchInput = screen.getByPlaceholderText(/enter search term.../i);
    const searchButton = screen.getByRole('button', { name: /search/i });

    fireEvent.change(searchInput, { target: { value: 'banana' } });
    fireEvent.click(searchButton);

    await waitFor(() => expect(screen.getByText(/message with banana search result 2/i)).toBeInTheDocument());
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('search=banana');
  });
});
```
