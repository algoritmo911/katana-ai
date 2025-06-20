import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import LogConfiguration from '../LogConfiguration';

// Mock global fetch
global.fetch = jest.fn();

const mockStatusResponse = (level: string, logFile: string = '/var/log/katana_events.log') => ({
  level,
  log_file: logFile,
});

// Helper to mock fetch responses
const mockFetchImplementation = (data: any, ok: boolean = true, status: number = 200) => {
  return Promise.resolve({
    ok,
    status,
    json: async () => data,
    statusText: ok ? 'OK' : `Mock Error ${status}`,
  } as Response);
};


describe('LogConfiguration Component', () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
    // jest.useFakeTimers(); // If using timers for clearing messages
  });

  // afterEach(() => {
  //   jest.clearAllTimers(); // If using timers
  // });

  test('renders loading state initially for status', () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() =>
      new Promise(() => {}) // Simulate pending promise for status fetch
    );
    render(<LogConfiguration />);
    expect(screen.getByText(/loading status.../i)).toBeInTheDocument();
  });

  test('displays current log status after successful fetch', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(
        mockFetchImplementation(mockStatusResponse('INFO', 'test.log'))
    );
    render(<LogConfiguration />);
    await waitFor(() => expect(screen.getByText(/application log level: info/i)).toBeInTheDocument());
    expect(screen.getByText(/log file path: test.log/i)).toBeInTheDocument();

    const levelSelect = screen.getByLabelText(/new log level/i);
    expect(levelSelect).toHaveValue('INFO');
  });

  test('displays error message if fetching status fails', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Status Error'));
    render(<LogConfiguration />);
    await waitFor(() => expect(screen.getByText(/error fetching status: api status error/i)).toBeInTheDocument());
  });

  test('allows changing the log level and reflects update', async () => {
    // 1. Initial status fetch
    (global.fetch as jest.Mock).mockResolvedValueOnce(
        mockFetchImplementation(mockStatusResponse('INFO'))
    );
    // 2. POST request for setting level
    (global.fetch as jest.Mock).mockResolvedValueOnce(
        mockFetchImplementation({ message: 'Log level set to DEBUG' })
    );
    // 3. Fetch status again after update
    (global.fetch as jest.Mock).mockResolvedValueOnce(
        mockFetchImplementation(mockStatusResponse('DEBUG')) // New status
    );

    render(<LogConfiguration />);
    // Wait for initial status and select to be populated
    await waitFor(() => expect(screen.getByLabelText(/new log level/i)).toHaveValue('INFO'));

    const levelSelect = screen.getByLabelText(/new log level/i);
    fireEvent.change(levelSelect, { target: { value: 'DEBUG' } });
    expect(levelSelect).toHaveValue('DEBUG'); // UI reflects selection

    const setLevelButton = screen.getByRole('button', { name: /set level/i });
    fireEvent.click(setLevelButton);

    // Check for updating message (might be too quick to catch reliably without pausing)
    // Instead, we'll wait for the success/final state.
    // If needed: expect(screen.getByText(/updating.../i)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText(/log level set to debug/i)).toBeInTheDocument(), {timeout: 2000});
    await waitFor(() => expect(screen.getByText(/application log level: debug/i)).toBeInTheDocument(), {timeout: 2000});
    expect(screen.getByLabelText(/new log level/i)).toHaveValue('DEBUG'); // Select should reflect new current status

    // Verify POST call
    expect(global.fetch).toHaveBeenCalledWith('/api/logs/level', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level: 'DEBUG' }),
    });
    expect(global.fetch).toHaveBeenCalledTimes(3); // Initial status, POST level, refresh status
  });

  test('displays error message if updating log level fails on POST', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce( // Initial status
      mockFetchImplementation(mockStatusResponse('INFO'))
    );
    (global.fetch as jest.Mock).mockResolvedValueOnce( // POST fails
      mockFetchImplementation({ detail: 'Server error during update' }, false, 500)
    );

    render(<LogConfiguration />);
    await waitFor(() => expect(screen.getByLabelText(/new log level/i)).toHaveValue('INFO'));

    fireEvent.change(screen.getByLabelText(/new log level/i), { target: { value: 'ERROR' } });
    fireEvent.click(screen.getByRole('button', { name: /set level/i }));

    await waitFor(() => expect(screen.getByText(/error updating log level: server error during update/i)).toBeInTheDocument());
    // Status should remain INFO because the update failed and fetchLogStatus wasn't called after error
    expect(screen.getByText(/application log level: info/i)).toBeInTheDocument();
  });

  test('displays error message if updating log level fails with network error', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce( // Initial status
      mockFetchImplementation(mockStatusResponse('INFO'))
    );
     // POST fails with network error
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network failure on POST'));

    render(<LogConfiguration />);
    await waitFor(() => expect(screen.getByLabelText(/new log level/i)).toHaveValue('INFO'));

    fireEvent.change(screen.getByLabelText(/new log level/i), { target: { value: 'ERROR' } });
    fireEvent.click(screen.getByRole('button', { name: /set level/i }));

    await waitFor(() => expect(screen.getByText(/error updating log level: network failure on post/i)).toBeInTheDocument());
    expect(screen.getByText(/application log level: info/i)).toBeInTheDocument();
  });


  test('"Set Level" button is disabled if selected level is same as current', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      mockFetchImplementation(mockStatusResponse('INFO'))
    );
    render(<LogConfiguration />);
    const setLevelButton = screen.getByRole('button', { name: /set level/i });
    const levelSelect = screen.getByLabelText(/new log level/i);

    await waitFor(() => expect(levelSelect).toHaveValue('INFO'));
    // Initially, selectedLevel (from status) is INFO, so button should be disabled
    expect(setLevelButton).toBeDisabled();

    // Change selection to something else, button should enable
    fireEvent.change(levelSelect, { target: { value: 'DEBUG' } });
    expect(setLevelButton).not.toBeDisabled();

    // Change back to INFO, button should disable again
    fireEvent.change(levelSelect, { target: { value: 'INFO' } });
    expect(setLevelButton).toBeDisabled();
  });

  test('success/error messages are cleared when selection changes', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(mockFetchImplementation(mockStatusResponse('INFO')));
    (global.fetch as jest.Mock).mockResolvedValueOnce(mockFetchImplementation({ message: 'Log level set to DEBUG' })); // For successful update
    (global.fetch as jest.Mock).mockResolvedValueOnce(mockFetchImplementation(mockStatusResponse('DEBUG')));


    render(<LogConfiguration />);
    await waitFor(() => expect(screen.getByLabelText(/new log level/i)).toHaveValue('INFO'));

    // Trigger a successful update
    fireEvent.change(screen.getByLabelText(/new log level/i), { target: { value: 'DEBUG' } });
    fireEvent.click(screen.getByRole('button', { name: /set level/i }));
    await waitFor(() => expect(screen.getByText(/log level set to debug/i)).toBeInTheDocument());

    // Now change selection, success message should disappear
    fireEvent.change(screen.getByLabelText(/new log level/i), { target: { value: 'WARNING' } });
    expect(screen.queryByText(/log level set to debug/i)).not.toBeInTheDocument();
  });

});
```
