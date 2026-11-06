/* Test-only dynamic interposition. No source buffers or arguments are logged. */
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <spawn.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>

int veilguard_guard_active(void) { return 1; }
static int report_fd = -1;
static void event(const char *name) {
    if (report_fd >= 0) { (void)write(report_fd, name, strlen(name)); }
}
__attribute__((constructor)) static void start(void) {
    const char *value = getenv("VEILGUARD_GUARD_FD");
    if (value) report_fd = atoi(value);
    event("guard_loaded\n");
}
__attribute__((destructor)) static void finish(void) { event("guard_finished\n"); }
static int vg_socket(int domain,int type,int protocol) { event("socket\n");errno=EPERM;return -1; }
static int vg_connect(int fd,const struct sockaddr *addr,socklen_t len) {event("connect\n");errno=EPERM;return -1;}
static ssize_t vg_sendto(int fd,const void *b,size_t n,int flags,const struct sockaddr *a,socklen_t l) {event("sendto\n");errno=EPERM;return -1;}
static int vg_getaddrinfo(const char *n,const char *s,const struct addrinfo *h,struct addrinfo **r) {event("getaddrinfo\n");errno=EPERM;return EAI_SYSTEM;}
static pid_t vg_fork(void) {event("fork\n");errno=EPERM;return -1;}
static pid_t vg_vfork(void) {event("vfork\n");errno=EPERM;return -1;}
static int vg_execve(const char *p,char *const a[],char *const e[]) {event("execve\n");errno=EPERM;return -1;}
static int vg_posix_spawn(pid_t *p,const char *n,const posix_spawn_file_actions_t *f,const posix_spawnattr_t *a,char *const v[],char *const e[]) {event("posix_spawn\n");return EPERM;}
static int vg_posix_spawnp(pid_t *p,const char *n,const posix_spawn_file_actions_t *f,const posix_spawnattr_t *a,char *const v[],char *const e[]) {event("posix_spawnp\n");return EPERM;}
#ifdef __APPLE__
#define INTERPOSE(replacement, original) \
__attribute__((used)) static struct { const void *replacement; const void *original; } ip_##original \
__attribute__((section("__DATA,__interpose"))) = {(const void *)(unsigned long)&replacement,(const void *)(unsigned long)&original};
INTERPOSE(vg_socket,socket)
INTERPOSE(vg_connect,connect)
INTERPOSE(vg_sendto,sendto)
INTERPOSE(vg_getaddrinfo,getaddrinfo)
INTERPOSE(vg_fork,fork)
INTERPOSE(vg_vfork,vfork)
INTERPOSE(vg_execve,execve)
INTERPOSE(vg_posix_spawn,posix_spawn)
INTERPOSE(vg_posix_spawnp,posix_spawnp)
#else
int socket(int d,int t,int p){return vg_socket(d,t,p);}
int connect(int f,const struct sockaddr *a,socklen_t l){return vg_connect(f,a,l);}
ssize_t sendto(int f,const void *b,size_t n,int g,const struct sockaddr *a,socklen_t l){return vg_sendto(f,b,n,g,a,l);}
int getaddrinfo(const char*n,const char*s,const struct addrinfo*h,struct addrinfo**r){return vg_getaddrinfo(n,s,h,r);}
pid_t fork(void){return vg_fork();}
pid_t vfork(void){return vg_vfork();}
int execve(const char*p,char*const a[],char*const e[]){return vg_execve(p,a,e);}
int posix_spawn(pid_t*p,const char*n,const posix_spawn_file_actions_t*f,const posix_spawnattr_t*a,char*const v[],char*const e[]){return vg_posix_spawn(p,n,f,a,v,e);}
int posix_spawnp(pid_t*p,const char*n,const posix_spawn_file_actions_t*f,const posix_spawnattr_t*a,char*const v[],char*const e[]){return vg_posix_spawnp(p,n,f,a,v,e);}
#endif
