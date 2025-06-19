import React from 'react';
import ServiceCard, { Service } from './ServiceCard';

interface ServiceGridProps {
  services: Service[];
  onConnectToggle: (serviceId: string) => void;
  onSettingsClick: (serviceId: string) => void;
}

const ServiceGrid: React.FC<ServiceGridProps> = ({ services, onConnectToggle, onSettingsClick }) => {
  if (!services || services.length === 0) { // Added null check for services
    return <p className="text-center text-gray-500 dark:text-gray-400 py-8">No services available to connect.</p>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {services.map((service) => (
        <ServiceCard
          key={service.id}
          service={service}
          onConnectToggle={onConnectToggle}
          onSettingsClick={onSettingsClick}
        />
      ))}
    </div>
  );
};

export default ServiceGrid;
