%bcond_without pam
%bcond_without audit
%bcond_without inotify

Summary:	Cron daemon for executing programs at set times
Name:		cronie
Version:	1.4.11
Release:	12
License:	MIT and BSD
Group:		System/Servers
URL:		https://fedorahosted.org/cronie
Source0:	https://fedorahosted.org/releases/c/r/cronie/%{name}-%{version}.tar.gz
Source1:	anacron-timestamp
Source2:	crond.pam
Patch0:		cronie-1.4.8-lsb_header_fix.patch
Patch1:		correct-env.patch
Patch2:		unitfile-killprocess.patch

%if %{with pam}
Requires:	pam
Buildrequires:	pam-devel
%endif
%if %{with audit}
Buildrequires:	audit-devel
%endif
Requires:	syslog-daemon
Requires(post): rpm-helper
Requires(preun): rpm-helper
Suggests:	anacron
Conflicts:	sysklogd < 1.4.1
Provides:	cron-daemon
Provides:	vixie-cron = 4:4.4
Obsoletes:	vixie-cron <= 4:4.3

%description
Cronie contains the standard UNIX daemon crond that runs specified programs at
scheduled times and related tools. It is a fork of the original vixie-cron and
has security and configuration enhancements like the ability to use pam and
SELinux.

%package anacron
Summary:	Utility for running regular jobs
Group:		System/Servers
Requires:	crontabs
# for touch
Requires(post):	coreutils
Provides:	anacron = 2.4
Obsoletes:	anacron < 2.4

%description anacron
Anacron becames part of cronie. Anacron is used only for running regular jobs.
The default settings execute regular jobs by anacron, however this could be
overloaded in settings.

%prep
%setup -q
%apply_patches

# Make sure anacron is started after regular cron jobs, otherwise anacron might
# run first, and after that regular cron runs the same jobs again
sed -i	-e "s/^START_HOURS_RANGE.*$/START_HOURS_RANGE=6-22/" \
	-e "s/nice run-parts/nice -n 19 run-parts/" \
	contrib/anacrontab

%build
%serverbuild
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
%makeinstall_std

install -d -m 700 %{buildroot}/var/spool/cron
install -d -m 755 %{buildroot}%{_sysconfdir}/cron.d

# https://bugzilla.mandriva.com/show_bug.cgi?id=19645 and
# https://bugzilla.mandriva.com/show_bug.cgi?id=28278
touch %{buildroot}%{_sysconfdir}/cron.deny

install -d %{buildroot}%{_sysconfdir}/sysconfig
install -m0644 crond.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/crond

install -m 644 contrib/anacrontab %{buildroot}%{_sysconfdir}/anacrontab
mkdir -pm 755 %{buildroot}%{_sysconfdir}/cron.hourly
install -c -m755 contrib/0anacron %{buildroot}%{_sysconfdir}/cron.hourly/0anacron

install -m644 %{SOURCE2} %{buildroot}%{_sysconfdir}/pam.d/crond

# Install cron job which will update anacron's daily, weekly, monthly timestamps
# when these jobs are run by regular cron, in order to prevent duplicate execution
for i in daily weekly monthly
do
mkdir -p %{buildroot}/etc/cron.${i}
sed -e "s/XXXX/${i}/" %{SOURCE1} > %{buildroot}/etc/cron.${i}/0anacron-timestamp
done

# create empty %ghost files
mkdir -p %{buildroot}/var/spool/anacron
touch %{buildroot}/var/spool/anacron/cron.daily
touch %{buildroot}/var/spool/anacron/cron.weekly
touch %{buildroot}/var/spool/anacron/cron.monthly

%if ! %{with pam}
rm -f %{buildroot}%{_sysconfdir}/pam.d/crond
%endif

# install systemd initscript
mkdir -p %{buildroot}%{_unitdir}
install -m 644 contrib/cronie.systemd %{buildroot}%{_unitdir}/crond.service

%post
%_post_service crond

%post anacron
[ -e /var/spool/anacron/cron.daily ] || touch /var/spool/anacron/cron.daily
[ -e /var/spool/anacron/cron.weekly ] || touch /var/spool/anacron/cron.weekly
[ -e /var/spool/anacron/cron.monthly ] || touch /var/spool/anacron/cron.monthly

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

%triggerin -- pam, glibc
/bin/systemctl try-restart crond.service >/dev/null 2>&1 || :

%files
%doc AUTHORS COPYING INSTALL README ChangeLog
%attr(755,root,root) %{_sbindir}/crond
%attr(6755,root,root) %{_bindir}/crontab
%{_mandir}/man8/crond.*
%{_mandir}/man8/cron.*
%{_mandir}/man5/crontab.*
%{_mandir}/man1/crontab.*
%dir /var/spool/cron
%dir %{_sysconfdir}/cron.d
%if %{with pam}
%attr(0644,root,root) %config(noreplace) %{_sysconfdir}/pam.d/crond
%endif
%config(noreplace) %{_sysconfdir}/sysconfig/crond
%config(noreplace) %{_sysconfdir}/cron.deny
%attr(0644,root,root) %{_unitdir}/crond.service

%files anacron
%{_sbindir}/anacron
%config(noreplace) %{_sysconfdir}/anacrontab
%attr(0755,root,root) %{_sysconfdir}/cron.daily/0anacron-timestamp
%attr(0755,root,root) %{_sysconfdir}/cron.weekly/0anacron-timestamp
%attr(0755,root,root) %{_sysconfdir}/cron.monthly/0anacron-timestamp
%attr(0755,root,root) %{_sysconfdir}/cron.hourly/0anacron
%dir /var/spool/anacron
%ghost %verify(not md5 size mtime) /var/spool/anacron/cron.daily
%ghost %verify(not md5 size mtime) /var/spool/anacron/cron.weekly
%ghost %verify(not md5 size mtime) /var/spool/anacron/cron.monthly
%{_mandir}/man5/anacrontab.*
%{_mandir}/man8/anacron.*

