import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import KatanaControls from './KatanaControls';

const mockEmit = jest.fn();
const mockSocket = {
  on: jest.fn(),
  off: jest.fn(),
  emit: mockEmit,
  connected: true,
  disconnect: jest.fn(),
};
jest.mock('socket.io-client', () => ({
  __esModule: true,
  default: jest.fn(() => mockSocket),
}));

jest.mock('react-toastify', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
  },
}));

describe('KatanaControls Component', () => {
  beforeEach(() => {
    mockEmit.mockClear();
    mockSocket.on.mockClear();
    mockSocket.off.mockClear();
    mockSocket.disconnect.mockClear();
    mockSocket.connected = true;
  });

  test('renders without crashing', () => {
    render(<KatanaControls />);
    expect(screen.getByText('Katana Agent Controls')).toBeInTheDocument();
  });

  test('renders control buttons', () => {
    render(<KatanaControls />);
    expect(screen.getByRole('button', { name: /ping agent/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload core settings/i })).toBeInTheDocument();
  });

  test('clicking "Ping Agent" button emits ping_agent event', () => {
    render(<KatanaControls />);
    fireEvent.click(screen.getByRole('button', { name: /ping agent/i }));
    expect(mockEmit).toHaveBeenCalledWith('ping_agent', { data: 'ping_payload_if_any' });
  });

  test('clicking "Reload Core Settings" button shows confirmation and emits event if confirmed', () => {
    const mockConfirm = jest.spyOn(window, 'confirm').mockImplementation(() => true);
    render(<KatanaControls />);
    fireEvent.click(screen.getByRole('button', { name: /reload core settings/i }));
    expect(mockConfirm).toHaveBeenCalledTimes(1);
    expect(mockEmit).toHaveBeenCalledWith('reload_settings_command', { data: 'reload_payload_if_any' });
    mockConfirm.mockRestore();
  });

  test('clicking "Reload Core Settings" button does not emit event if not confirmed', () => {
    const mockConfirm = jest.spyOn(window, 'confirm').mockImplementation(() => false);
    render(<KatanaControls />);
    fireEvent.click(screen.getByRole('button', { name: /reload core settings/i }));
    expect(mockConfirm).toHaveBeenCalledTimes(1);
    expect(mockEmit).not.toHaveBeenCalledWith('reload_settings_command', expect.anything());
    mockConfirm.mockRestore();
  });
});
