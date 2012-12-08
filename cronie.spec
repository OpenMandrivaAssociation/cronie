%bcond_without pam
%bcond_without audit
%bcond_without inotify

Summary:	Cron daemon for executing programs at set times
Name:		cronie
Version:	1.4.8
Release:	3
License:	MIT and BSD
Group:		System/Servers
URL:		https://fedorahosted.org/cronie
Source0:	https://fedorahosted.org/releases/c/r/cronie/%{name}-%{version}.tar.gz
Source1:	anacron-timestamp
Source2:	crond.pam
Source3:	cronie.systemd
Patch0:		cronie-1.4.8-lsb_header_fix.patch
%if %{with pam}
Requires:	pam
Buildrequires:	pam-devel
%endif
%if %{with audit}
Buildrequires:	audit-libs-devel
%endif
Requires:	syslog-daemon
Provides:	cron-daemon
Requires(pre):	/sbin/chkconfig
Requires(post):	systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
Requires(post):	systemd-sysvinit
Requires(post): rpm-helper
Requires(preun): rpm-helper
Suggests:	anacron
Conflicts:	sysklogd < 1.4.1
Provides:	cron-daemon
Provides:	vixie-cron = 4:4.4
Obsoletes:	vixie-cron <= 4:4.3
Buildroot:	%{_tmppath}/%{name}-%{version}-%{release}-buildroot

%description
Cronie contains the standard UNIX daemon crond that runs specified programs at
scheduled times and related tools. It is a fork of the original vixie-cron and
has security and configuration enhancements like the ability to use pam and
SELinux.

%package anacron
Summary:	Utility for running regular jobs
Requires:	crontabs
# for touch
Requires(post):	coreutils
Group:		System/Servers
Provides:	anacron = 2.4
Obsoletes:	anacron < 2.4

%description anacron
Anacron becames part of cronie. Anacron is used only for running regular jobs.
The default settings execute regular jobs by anacron, however this could be
overloaded in settings.

%prep
%setup -q -n %{name}-%{version}
%patch0 -p1

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
mkdir -p %buildroot%{_unitdir}
install -m 644 %SOURCE3 %buildroot%{_unitdir}/crond.service

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


%changelog
* Tue Sep 27 2012 akdengi <akdengi> 1.4.8-3
- clean spec
- add LSB patch
- dprop SysVinit

* Tue Oct 11 2011 Tomasz Pawel Gajc <tpg@mandriva.org> 1.4.8-2mdv2012.0
+ Revision: 704375
- add support for systemd
- update to new version 1.4.8
- use %%serverbuild_hardened macro for mdv2012

* Tue May 03 2011 Oden Eriksson <oeriksson@mandriva.com> 1.4.7-2
+ Revision: 663426
- mass rebuild

* Thu Mar 17 2011 Oden Eriksson <oeriksson@mandriva.com> 1.4.7-1
+ Revision: 646048
- 1.4.7
- drop upstream fixed patch

* Tue Jan 04 2011 Ahmad Samir <ahmadsamir@mandriva.org> 1.4.4-4mdv2011.0
+ Revision: 628635
- rebuild to pick _PATH_VI changes from mdv bug#60929

* Tue Nov 30 2010 Oden Eriksson <oeriksson@mandriva.com> 1.4.4-3mdv2011.0
+ Revision: 603859
- rebuild

* Mon Mar 15 2010 Oden Eriksson <oeriksson@mandriva.com> 1.4.4-2mdv2010.1
+ Revision: 519979
- rebuilt against audit-2 libs

* Sun Mar 07 2010 Sandro Cazzaniga <kharec@mandriva.org> 1.4.4-1mdv2010.1
+ Revision: 515591
- drop old patch not needed anymore
- update to 1.4.4

* Sun Jan 03 2010 Frederik Himpe <fhimpe@mandriva.org> 1.4.3-3mdv2010.1
+ Revision: 485759
- Really fix pam configuration

* Sat Jan 02 2010 Frederik Himpe <fhimpe@mandriva.org> 1.4.3-2mdv2010.1
+ Revision: 484952
- Add upstream patch to fix pam authentication (bug #56773)

* Fri Jan 01 2010 Emmanuel Andry <eandry@mandriva.org> 1.4.3-1mdv2010.1
+ Revision: 484753
- New version 1.4.3

* Thu Sep 24 2009 Olivier Blin <blino@mandriva.org> 1.4.1-5mdv2010.0
+ Revision: 448231
- link with audit (from Arnaud Patard)
  When enabling audit, it's better to actually link with it.
  For now, it's fine thanks to pam with audit support but still,
  this remains buggy

* Mon Aug 24 2009 Frederik Himpe <fhimpe@mandriva.org> 1.4.1-4mdv2010.0
+ Revision: 420634
- Execute run-parts with nice -n 19 in anacrontab, just like /etc/crontab

* Thu Aug 20 2009 Frederik Himpe <fhimpe@mandriva.org> 1.4.1-3mdv2010.0
+ Revision: 418733
- Make anacron-timestamp scripts executable
- Rename anacron-timestamp in order to start before normal cron jobs, so
  that anacron will never start while jobs started by crond are still running

* Wed Aug 19 2009 Frederik Himpe <fhimpe@mandriva.org> 1.4.1-2mdv2010.0
+ Revision: 418313
- Use official 1.4.1 tarball and use included anacrontab
- Mark /var/spool/anacron files as %%ghost and create them in %%post (Fedora)
- Fix problems from bug #52952:
  * Don't create /etc/cron.d/0hourly cron job which starts hourly cron jobs,
    it results in double execution
  * Add daily, weekly, monthly cronjobs to update anacron's timestamp files,
    in order to prevent unnecessary anacron runs
  * Only start anacron after 6h in anacrontab, in order to prevent double
    execution if anacron is started before regular cron jobs are run
  * Fix check for anacron's timestamp files in /etc/cron.hourly/0anacron

* Wed Aug 05 2009 Frederik Himpe <fhimpe@mandriva.org> 1.4.1-1mdv2010.0
+ Revision: 410339
- Fix group
- Update to new version 1.4.1 (taken from git 1.4.1 tag because no
  source tarball was published)
- Build included anacron 2.4, obsoleting anacron package
- Add missing anacrontab (taken from cronie git)

* Tue Jul 21 2009 Frederik Himpe <fhimpe@mandriva.org> 1.4-1mdv2010.0
+ Revision: 398371
- Update to new version 1.4

* Sat May 02 2009 Frederik Himpe <fhimpe@mandriva.org> 1.3-1mdv2010.0
+ Revision: 370372
- Update to new version 1.3
- Drop RH patches (also dropped in RH, because the problems they fix
  have been fixed upstream)

* Fri Jan 30 2009 Oden Eriksson <oeriksson@mandriva.com> 1.2-2mdv2009.1
+ Revision: 335467
- remove deps on sendmail-command

* Fri Jan 30 2009 Oden Eriksson <oeriksson@mandriva.com> 1.2-1mdv2009.1
+ Revision: 335426
- import cronie


* Fri Jan 30 2009 Oden Eriksson <oeriksson@mandriva.com> 1.2-1mdv2009.1
- initial Mandriva package (fedora import)

* Tue Dec 23 2008 Marcela Mašláňová <mmaslano@redhat.com> - 1.2-5
- 477100 NO_FOLLOW was removed, reload after change in symlinked
  crontab is needed, man updated.

* Fri Oct 24 2008 Marcela Mašláňová <mmaslano@redhat.com> - 1.2-4
- update init script

* Thu Sep 25 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.2-3
- add sendmail file into requirement, cause it's needed some MTA

* Thu Sep 18 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.2-2
- 462252  /etc/sysconfig/crond does not need to be executable 

* Thu Jun 26 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.2-1
- update to 1.2

* Tue Jun 17 2008 Tomas Mraz <tmraz@redhat.com> - 1.1-3
- fix setting keycreate context
- unify logging a bit
- cleanup some warnings and fix a typo in TZ code
- 450993 improve and fix inotify support

* Wed Jun  4 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.1-2
- 49864 upgrade/update problem. Syntax error in spec.

* Wed May 28 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.1-1
- release 1.1

* Tue May 20 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-6
- 446360 check for lock didn't call chkconfig

* Tue Feb 12 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-5
- upgrade from less than cronie-1.0-4 didn't add chkconfig

* Wed Feb  6 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-4
- 431366 after reboot wasn't cron in chkconfig

* Tue Feb  5 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-3
- 431366 trigger part => after update from vixie-cron on cronie will 
	be daemon running.

* Wed Jan 30 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-2
- change the provides on higher version than obsoletes

* Tue Jan  8 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-1
- packaging cronie
- thank's for help with packaging to my reviewers
