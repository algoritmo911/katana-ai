import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CommandSender from './CommandSender';
import { toast } from 'react-toastify';

const mockEmitCmd = jest.fn();
const mockSocketCmd = {
  on: jest.fn(),
  off: jest.fn(),
  emit: mockEmitCmd,
  connected: true,
  disconnect: jest.fn(),
};
jest.mock('socket.io-client', () => ({
  __esModule: true,
  default: jest.fn(() => mockSocketCmd),
}));

jest.mock('react-toastify', () => ({
  ...jest.requireActual('react-toastify'),
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  }
}));

describe('CommandSender Component', () => {
  beforeEach(() => {
    mockEmitCmd.mockClear();
    mockSocketCmd.on.mockClear();
    mockSocketCmd.off.mockClear();
    mockSocketCmd.disconnect.mockClear();
    mockSocketCmd.connected = true;
    toast.error.mockClear();
    toast.success.mockClear();
  });

  test('renders correctly', () => {
    render(<CommandSender />);
    expect(screen.getByText('Send Custom Command')).toBeInTheDocument();
    expect(screen.getByLabelText(/action/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/parameters \(json format\)/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send command/i })).toBeInTheDocument();
  });

  test('allows typing into action and parameters fields', () => {
    render(<CommandSender />);
    const actionInput = screen.getByLabelText(/action/i);
    const paramsInput = screen.getByLabelText(/parameters \(json format\)/i);
    fireEvent.change(actionInput, { target: { value: 'test_action' } });
    fireEvent.change(paramsInput, { target: { value: '{"key":"value"}' } });
    expect(actionInput.value).toBe('test_action');
    expect(paramsInput.value).toBe('{"key":"value"}');
  });

  test('clicking "Send Command" emits send_command_to_katana with correct data', () => {
    render(<CommandSender />);
    const actionInput = screen.getByLabelText(/action/i);
    const paramsInput = screen.getByLabelText(/parameters \(json format\)/i);
    const sendButton = screen.getByRole('button', { name: /send command/i });
    fireEvent.change(actionInput, { target: { value: 'do_something' } });
    fireEvent.change(paramsInput, { target: { value: '{"param1": 123}' } });
    fireEvent.click(sendButton);
    expect(mockEmitCmd).toHaveBeenCalledWith('send_command_to_katana', {
      action: 'do_something',
      parameters: '{"param1": 123}',
    });
  });

  test('shows error toast if action is empty', () => {
    render(<CommandSender />);
    const sendButton = screen.getByRole('button', { name: /send command/i });
    fireEvent.click(sendButton);
    expect(toast.error).toHaveBeenCalledWith('Action cannot be empty.');
    expect(mockEmitCmd).not.toHaveBeenCalled();
  });

  test('shows error toast if parameters are invalid JSON', () => {
    render(<CommandSender />);
    const actionInput = screen.getByLabelText(/action/i);
    const paramsInput = screen.getByLabelText(/parameters \(json format\)/i);
    const sendButton = screen.getByRole('button', { name: /send command/i });
    fireEvent.change(actionInput, { target: { value: 'valid_action' } });
    fireEvent.change(paramsInput, { target: { value: 'not json' } });
    fireEvent.click(sendButton);
    expect(toast.error).toHaveBeenCalledWith('Parameters field must contain valid JSON.');
    expect(mockEmitCmd).not.toHaveBeenCalled();
  });
});
