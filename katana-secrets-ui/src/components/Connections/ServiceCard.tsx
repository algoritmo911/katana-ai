import React from 'react';

export interface Service {
  id: string;
  name: string;
  logoUrl?: string;
  description?: string;
  status: 'connected' | 'disconnected' | 'error' | 'pending';
}

interface ServiceCardProps {
  service: Service;
  onConnectToggle: (serviceId: string) => void;
  onSettingsClick: (serviceId: string) => void;
}

const ServiceCard: React.FC<ServiceCardProps> = ({ service, onConnectToggle, onSettingsClick }) => {
  const getStatusClasses = () => {
    switch (service.status) {
      case 'connected':
        return 'bg-green-100 text-green-700 border-green-300';
      case 'disconnected':
        return 'bg-gray-100 text-gray-700 border-gray-300';
      case 'error':
        return 'bg-red-100 text-red-700 border-red-300';
      case 'pending':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getButtonText = () => {
    switch (service.status) {
      case 'connected':
        return 'Disconnect';
      case 'disconnected':
        return 'Connect';
      case 'error':
        return 'Retry';
      case 'pending':
        return 'Pending...';
      default:
        return 'Connect';
    }
  };

  const getButtonClasses = () => {
     switch (service.status) {
      case 'connected':
        return 'bg-red-500 hover:bg-red-600 text-white';
      case 'disconnected':
        return 'bg-blue-500 hover:bg-blue-600 text-white';
      case 'error':
        return 'bg-yellow-500 hover:bg-yellow-600 text-black'; // Changed text to black for yellow bg
      case 'pending':
        return 'bg-gray-400 text-gray-800 cursor-not-allowed';
      default:
        return 'bg-blue-500 hover:bg-blue-600 text-white';
    }
  }

  return (
    <div className={`border dark:border-gray-700 rounded-lg shadow-md p-6 flex flex-col justify-between items-center text-center ${getStatusClasses().split(' ')[0].replace('bg-', 'border-t-4 border-')}`}>
      <div>
        {service.logoUrl ? (
          <img src={service.logoUrl} alt={`${service.name} logo`} className="h-16 w-16 mx-auto mb-4 object-contain" />
        ) : (
          <div className="h-16 w-16 mx-auto mb-4 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center text-2xl font-bold text-gray-500 dark:text-gray-400">
            {service.name.substring(0, 1).toUpperCase()}
          </div>
        )}
        <h3 className="text-xl font-semibold mb-2 text-gray-800 dark:text-gray-100">{service.name}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 h-10 overflow-hidden">
          {service.description || `Connect to ${service.name} to sync data.`}
        </p>
         <p className={`text-xs font-medium py-1 px-2 rounded-full inline-block mb-4 ${getStatusClasses()}`}>
          Status: {service.status.charAt(0).toUpperCase() + service.status.slice(1)}
        </p>
      </div>
      <div className="w-full mt-auto"> {/* Ensure buttons are at the bottom */}
        <button
          onClick={() => onConnectToggle(service.id)}
          disabled={service.status === 'pending'}
          className={`w-full py-2 px-4 rounded-md font-semibold text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 dark:ring-offset-gray-800 mb-2 ${getButtonClasses()} disabled:opacity-70`}
        >
          {getButtonText()}
        </button>
        {service.status === 'connected' && (
          <button
            onClick={() => onSettingsClick(service.id)}
            className="w-full py-2 px-4 rounded-md font-semibold text-sm bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-700 dark:text-gray-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:ring-offset-gray-800"
          >
            Settings
          </button>
        )}
      </div>
    </div>
  );
};

export default ServiceCard;
