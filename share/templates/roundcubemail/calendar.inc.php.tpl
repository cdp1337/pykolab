<?php
    \$config['calendar_driver'] = "kolab";
    \$config['calendar_default_view'] = "agendaWeek";
    \$config['calendar_timeslots'] = 2;
    \$config['calendar_first_day'] = 1;
    \$config['calendar_first_hour'] = 6;
    \$config['calendar_work_start'] = 6;
    \$config['calendar_work_end'] = 18;
    \$config['calendar_event_coloring'] = 0;
    \$config['calendar_caldav_url'] = 'http://%h/iRony/calendars/%u/%i';

    \$config['calendar_itip_smtp_server'] = '';
    \$config['calendar_itip_smtp_user'] = '';
    \$config['calendar_itip_smtp_pass'] = '';

    \$config['calendar_itip_send_option'] = 3;
    \$config['calendar_itip_after_action'] = 0;

    \$config['calendar_freebusy_trigger'] = false;

    \$config['kolab_invitation_calendars'] = false;

    \$config['calendar_contact_birthdays'] = true;

    \$config['calendar_resources_driver'] = 'ldap';

    \$config['calendar_resources_directory'] = array(
            'name'                  => 'Kolab Resources',
            'hosts'                 => 'localhost',
            'port'                  => 389,
            'use_tls'               => false,
            'base_dn'               => '$ldap_resource_base_dn',
            'user_specific'         => true,
            'bind_dn'               => '%dn',
            'bind_pass'             => '',
            'search_base_dn'        => '$ldap_user_base_dn',
            'search_bind_dn'        => '$ldap_service_bind_dn',
            'search_bind_pw'        => '$ldap_service_bind_pw',
            'search_filter'         => '(&(objectClass=inetOrgPerson)(mail=%fu))',
            'ldap_version'          => 3,
            'filter'                => '$ldap_resource_filter',
            'search_fields'         => array('cn'),
            'sort'                  => array('cn'),
            'scope'                 => 'sub',
            'fuzzy_search'          => true,
            'fieldmap'              => array(
                    // Internal     => LDAP
                    'name'          => 'cn',
                    'email'         => 'mail',
                    'owner'         => 'owner',
                    'description'   => 'description',
                    'attributes'    => 'kolabdescattribute',
                    'members'       => 'uniquemember',
                    // these mappings are required for owner display
                    'phone'         => 'telephoneNumber',
                    'mobile'        => 'mobile',
                ),

            'class_type_map'        => array(
                    'kolabsharedfolder'     => 'resource',
                    'groupofuniquenames'    => 'collection',
                ),

            'groups'                => array(
                    'name_attr'     => 'cn',
                ),
        );

    if (file_exists(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

?>
