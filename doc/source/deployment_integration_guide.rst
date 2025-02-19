Deployment tool integration
===========================

The ``networking-ovn`` repository includes integration with DevStack that
enables creation of a simple Open Virtual Network (OVN) development and test
environment. Deploying OVN in a realistic deployment requires integration
with various OpenStack deployment tools such as Fuel, OpenStack Ansible,
and TripleO. This guide provides general instructions for developers of these
tools to integrate OVN into conventional architectures that include the
following types of nodes:

* Controller - Runs OpenStack control plane services such as REST APIs
  and databases.

* Network - Runs the layer-2, layer-3 (routing), DHCP, and metadata agents
  for the Networking service. Some agents optional. Usually provides
  connectivity between provider (public) and project (private) networks
  via NAT and floating IP addresses.

  .. note::

     Some tools deploy these services on controller nodes.

* Compute - Runs the hypervisor and layer-2 agent for the Networking
  service.

Packaging
---------

Open vSwitch (OVS) includes OVN beginning with version 2.5 and considers
it experimental. The Networking service integration for OVN uses an
independent package, typically ``networking-ovn``.

Building OVS from source automatically installs OVN. For deployment tools
using distribution packages, the ``openvswitch-ovn`` package for RHEL/CentOS
and compatible distributions automatically installs ``openvswitch`` as a
dependency. Ubuntu/Debian and compatible distributions do not offer OVN
packages yet.

Controller nodes
----------------

Each controller node runs the OVS service (including dependent services such
as ``ovsdb-server``) and the ``ovn-northd`` service. However, only a single
instance of the ``ovsdb-server`` and ``ovn-northd`` services can operate in
a deployment. However, deployment tools can implement active/passive
high-availability using a management tool that monitors service health
and automatically starts these services on another node after failure of the
primary node. See the :ref:`faq` for more information.

#. Install the ``openvswitch-ovn`` and ``networking-ovn`` packages.

#. Start the OVS service. The central OVS service starts the ``ovsdb-server``
   service that manages OVN databases.

   Using the *systemd* unit:

   .. code-block:: console

      # systemctl start openvswitch

   Using the ``ovs-ctl`` script:

   .. code-block:: console

      # /usr/share/openvswitch/scripts/ovs-ctl start

#. Configure the ``ovsdb-server`` component. By default, the ``ovsdb-server``
   service only permits local access to databases via Unix socket. However,
   OVN services on compute nodes require access to these databases.

   * Permit remote database access.

     .. code-block:: console

        # ovs-appctl -t ovsdb-server ovsdb-server/add-remote ptcp:6640:IP_ADDRESS

     Replace ``IP_ADDRESS`` with the IP address of the management network
     interface on the controller node.

     .. note::

        Permit remote access to TCP port 6640 on any host firewall.

#. Start the ``ovn-northd`` service.

   Using the *systemd* unit:

   .. code-block:: console

      # systemctl start ovn-northd

   Using the ``ovn-ctl`` script:

   .. code-block:: console

      # /usr/share/openvswitch/scripts/ovn-ctl start_northd

#. Configure the Networking server component. The Networking service
   implements OVN as a core plug-in similar to ML2. Edit the
   ``/etc/neutron/neutron.conf`` file:

   * Enable the OVN core plug-in and disable any service plug-ins.

     .. code-block:: ini

        [DEFAULT]
        ...
        core_plugin = networking_ovn.plugin.OVNPlugin
        service_plugins =

     .. note::

        Disabling any service plug-ins applies to deployments using
        the OVN native layer-3 service or conventional layer-3 agent.

#. Configure the OVN plug-in. Edit the
   ``/etc/neutron/plugins/networking-ovn/networking-ovn.ini`` file:

   * Configure OVS database access.

     .. code-block:: ini

        [ovn]
        ...
        ovsdb_connection = tcp:IP_ADDRESS:6640

     Replace ``IP_ADDRESS`` with the IP address of the controller node
     that runs the ``ovsdb-server`` service.

   * (Optional) Enable native layer-3 services.

     .. code-block:: ini

        [ovn]
        ...
        ovn_l3_mode = True

     .. note::

        See :ref:`features` and :ref:`faq` for more information.

#. Start the ``neutron-server`` service.

   .. code-block:: console

      # systemctl start neutron-server

Network nodes
-------------

Deployments using native layer-3 services do not require conventional
network nodes because connectivity to external networks (including VTEP
gateways) and routing occurs on compute nodes. OVN currently relies on
conventional DHCP and metadata agents that typically operate on network
nodes. However, you can deploy these agents on controller nodes.

Compute nodes
-------------

Each compute node runs the OVS and ``ovn-controller`` services. The
``ovn-controller`` service replaces the conventional OVS layer-2 agent.

#. Install the ``openvswitch-ovn`` and ``networking-ovn`` packages.

#. Start the OVS service.

   Using the *systemd* unit:

   .. code-block:: console

      # systemctl start openvswitch

   Using the ``ovs-ctl`` script:

   .. code-block:: console

      # /usr/share/openvswitch/scripts/ovs-ctl start

#. Configure the OVS service.

   * Use OVS databases on the controller node.

     .. code-block:: console

        # ovs-vsctl set open . external-ids:ovn-remote=tcp:IP_ADDRESS:6640

     Replace ``IP_ADDRESS`` with the IP address of the controller node
     that runs the ``ovsdb-server`` service.

   * Enable one or more overlay network protocols. At a minimum, OVN requires
     enabling the ``geneve`` protocol. Deployments using VTEP gateways should
     also enable the ``vxlan`` protocol.

     .. code-block:: console

        # ovs-vsctl set open . external-ids:ovn-encap-type=geneve,vxlan

     .. note::

        Deployments without VTEP gateways can safely enable both protocols.

     .. note::

        Overlay network protocols generally require reducing MTU on VM
        interfaces to account for additional packet overhead. See the
        DHCP agent configuration in the
        `Installation Guide <http://docs.openstack.org/liberty/install-guide-ubuntu/neutron-controller-install-option2.html>`_
        for more information.

   * Configure the overlay network local endpoint IP address.

     .. code-block:: console

        # ovs-vsctl set open . external-ids:ovn-encap-ip=IP_ADDRESS

     Replace ``IP_ADDRESS`` with the IP address of the overlay network
     interface on the compute node.

#. Start the ``ovn-controller`` service.

   Using the *systemd* unit:

   .. code-block:: console

      # systemctl start ovn-controller

   Using the ``ovn-ctl`` script:

   .. code-block:: console

      # /usr/share/openvswitch/scripts/ovn-ctl start_controller

Verify operation
----------------

#. Each compute node should contain an ``ovn-controller`` instance.

   .. code-block:: console

      # ovn-sbctl show
        <output>
