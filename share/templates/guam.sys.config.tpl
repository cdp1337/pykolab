%% Example configuration for Guam.
[
    {
        kolab_guam, [
            {
                imap_servers, [
                    {
                        imaps, [
                            { host, "127.0.0.1" },
                            { port, 9993 },
                            { tls, true }
                        ]
                    }
                ]
            },
            {
                listeners, [
                    {
                        imap, [
                            { port, 143 },
                            { imap_server, imap },
                            {
                                rules, [
                                    { filter_groupware, [] }
                                ]
                            },
                            {
                                tls_config, [
                                    { certfile, "/etc/pki/cyrus-imapd/cyrus-imapd.pem" }
                                ]
                            }
                        ]
                    },
                    {
                        imaps, [
                            { port, 993 },
                            { implicit_tls, true },
                            { imap_server, imaps },
                            {
                                rules, [
                                    { filter_groupware, [] }
                                ]
                            },
                            {
                                tls_config, [
                                    { certfile, "/etc/pki/cyrus-imapd/cyrus-imapd.pem" }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },

    {
        lager, [
            {
                handlers, [
                    { lager_console_backend, warning },
                    { lager_file_backend, [ { file, "log/error.log"}, { level, error } ] },
                    { lager_file_backend, [ { file, "log/console.log"}, { level, info } ] }
                ]
            }
        ]
    },

    %% SASL config
    {
        sasl, [
            { sasl_error_logger, { file, "log/sasl-error.log" } },
            { errlog_type, error },
            { error_logger_mf_dir, "log/sasl" },      % Log directory
            { error_logger_mf_maxbytes, 10485760 },   % 10 MB max file size
            { error_logger_mf_maxfiles, 5 }           % 5 files max
        ]
    }
].
