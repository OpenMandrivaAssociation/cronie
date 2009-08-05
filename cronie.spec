%bcond_without pam
%bcond_without audit
%bcond_without inotify

Summary:	Cron daemon for executing programs at set times
Name:		cronie
Version:	1.4.1
Release:	%mkrel 1
License:	MIT and BSD
Group:		System/Servers
URL:		https://fedorahosted.org/cronie
#Source0: https://fedorahosted.org/cronie/%{name}-%{version}.tar.gz
Source0:	http://mmaslano.fedorapeople.org/cronie/%{name}-%{version}.tar.gz
Source1:	anacrontab
%if %{with pam}
Requires:	pam >= 0.77
Buildrequires:	pam-devel  >= 0.77
%endif
%if %{with audit}
Buildrequires:	audit-libs-devel >= 1.4.1
%endif
Requires:	syslog-daemon
Provides:	cron-daemon
Requires(post): rpm-helper
Requires(preun): rpm-helper
Suggests:	anacron
Conflicts:	sysklogd < 1.4.1
Provides:	vixie-cron = 4:4.4
Obsoletes:	vixie-cron <= 4:4.3
Buildroot:	%{_tmppath}/%{name}-%{version}-%{release}-buildroot

%description
Cronie contains the standard UNIX daemon crond that runs specified programs at
scheduled times and related tools. It is a fork of the original vixie-cron and
has security and configuration enhancements like the ability to use pam and
SELinux.

%package anacron
Summary: Utility for running regular jobs
Requires: crontabs
Group: System Environment/Base
Provides: anacron = 2.4
Obsoletes: anacron < 2.4

%description anacron
Anacron becames part of cronie. Anacron is used only for running regular jobs.
The default settings execute regular jobs by anacron, however this could be
overloaded in settings.


%prep
%setup -q -n %{name}

%build
%serverbuild
autoreconf -fis
%configure2_5x \
    --enable-anacron \
%if %{with pam}
    --with-pam \
%endif
%if %{with audit}
    --with-audit \
%endif
%if %{with inotify}
    --with-inotify 
%endif

%make

%install
rm -rf %{buildroot}

%makeinstall_std

install -d -m 700 %{buildroot}/var/spool/cron
install -d -m 755 %{buildroot}%{_sysconfdir}/cron.d

install -d -m 755 %{buildroot}%{_initrddir}
install -m 755 cronie.init %{buildroot}%{_initrddir}/crond

# https://bugzilla.mandriva.com/show_bug.cgi?id=19645 and
# https://bugzilla.mandriva.com/show_bug.cgi?id=28278
touch %{buildroot}%{_sysconfdir}/cron.deny

install -d %{buildroot}%{_sysconfdir}/sysconfig
install -m0644 crond.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/crond

install -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/anacrontab
install -c -m755 contrib/0hourly $RPM_BUILD_ROOT%{_sysconfdir}/cron.d/0hourly
mkdir -pm 755 $RPM_BUILD_ROOT%{_sysconfdir}/cron.hourly
install -c -m755 contrib/0anacron $RPM_BUILD_ROOT%{_sysconfdir}/cron.hourly/0anacron

%if ! %{with pam}
rm -f %{buildroot}%{_sysconfdir}/pam.d/crond
%endif

%post
%_post_service crond

%preun
%_preun_service crond

%postun
if [ "$1" -ge "1" ]; then
    service crond condrestart > /dev/null 2>&1 ||:
fi

# copy the lock, remove old daemon from chkconfig
%triggerun -- vixie-cron
cp -a /var/lock/subsys/crond /var/lock/subsys/cronie > /dev/null 2>&1 ||:

# if the lock exist, then we restart daemon (it was running in the past).
# add new daemon into chkconfig everytime, when we upgrade to cronie from vixie-cron
%triggerpostun -- vixie-cron
/sbin/chkconfig --add crond
[ -f /var/lock/subsys/cronie ] && ( rm -f /var/lock/subsys/cronie ; service crond restart ) > /dev/null 2>&1 ||:

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc AUTHORS COPYING INSTALL README ChangeLog
%attr(755,root,root) %{_sbindir}/crond
%attr(6755,root,root) %{_bindir}/crontab
%{_mandir}/man8/crond.*
%{_mandir}/man8/cron.*
%{_mandir}/man5/crontab.*
%{_mandir}/man1/crontab.*
%dir /var/spool/cron
%dir %{_sysconfdir}/cron.d
%{_initrddir}/crond
%if %{with pam}
%attr(0644,root,root) %config(noreplace) %{_sysconfdir}/pam.d/crond
%endif
%config(noreplace) %{_sysconfdir}/sysconfig/crond
%config(noreplace) %{_sysconfdir}/cron.deny

%files anacron
%defattr(-,root,root,-)
%{_sbindir}/anacron
%config(noreplace) %{_sysconfdir}/anacrontab
%attr(0644,root,root) %{_sysconfdir}/cron.d/0hourly
%attr(0755,root,root) %{_sysconfdir}/cron.hourly/0anacron
%{_mandir}/man5/anacrontab.*
%{_mandir}/man8/anacron.*
