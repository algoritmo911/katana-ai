import React from 'react';
import { Link, NavLink } from 'react-router-dom'; // Use NavLink for active styling

const Navbar: React.FC = () => {
  const activeClassName = "text-white bg-blue-700";
  const inactiveClassName = "text-gray-300 hover:bg-gray-700 hover:text-white";

  return (
    <nav className="bg-gray-800">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="text-white font-bold text-xl">
              Katana UI ⚔️
            </Link>
          </div>
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-4">
              <NavLink
                to="/dashboard"
                className={({ isActive }) => `${isActive ? activeClassName : inactiveClassName} px-3 py-2 rounded-md text-sm font-medium`}
              >
                Dashboard
              </NavLink>
              <NavLink
                to="/connections"
                className={({ isActive }) => `${isActive ? activeClassName : inactiveClassName} px-3 py-2 rounded-md text-sm font-medium`}
              >
                Connections
              </NavLink>
              <NavLink
                to="/memory"
                className={({ isActive }) => `${isActive ? activeClassName : inactiveClassName} px-3 py-2 rounded-md text-sm font-medium`}
              >
                Memory
              </NavLink>
              <NavLink
                to="/settings"
                className={({ isActive }) => `${isActive ? activeClassName : inactiveClassName} px-3 py-2 rounded-md text-sm font-medium`}
              >
                Settings
              </NavLink>
               <NavLink
                to="/onboarding"
                className={({ isActive }) => `${isActive ? activeClassName : inactiveClassName} px-3 py-2 rounded-md text-sm font-medium`}
              >
                Onboarding
              </NavLink>
              <NavLink
                to="/logs"
                className={({ isActive }) => `${isActive ? activeClassName : inactiveClassName} px-3 py-2 rounded-md text-sm font-medium`}
              >
                Logs
              </NavLink>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
