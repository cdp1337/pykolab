EXTRA_DIST = \
	wallace.sysconfig \
	wallace.systemd \
	wallace.sysvinit \
	wallace.tmpfiles.d.conf

wallacedir = $(pythondir)/wallace
wallace_PYTHON = \
	__init__.py \
	modules.py \
	$(wildcard module_*.py)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) \
		$(DESTDIR)/$(localstatedir)/run/wallaced
