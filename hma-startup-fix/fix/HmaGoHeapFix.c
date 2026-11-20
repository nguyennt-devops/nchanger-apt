/* HMA Go 1.16 iOS heap reservation compatibility fix.
 * Own a free low-address reservation before using MAP_FIXED. Never remove
 * another mapping, change heap index limits, or disable runtime checks.
 * Targets only mmap import slots in MimicNetworking, not process-wide mmap.
 */
typedef unsigned int u32;
typedef unsigned long long u64;
typedef unsigned long usize;
typedef long isize;
typedef unsigned char u8;
struct mach_header_64 {u32 magic,cpu,subcpu,type,ncmds,sizeofcmds,flags,reserved;};
struct load_command {u32 cmd,size;};
struct segment_64 {u32 cmd,size;char name[16];u64 vmaddr,vmsize,fileoff,filesize;u32 maxprot,initprot,nsects,flags;};
struct section_64 {char name[16],segment[16];u64 addr,size;u32 offset,align,reloff,nreloc,flags,reserved1,reserved2,reserved3;};
struct symtab_command {u32 cmd,size,symoff,nsyms,stroff,strsize;};
struct dysymtab_command {u32 cmd,size,ilocalsym,nlocalsym,iextdefsym,nextdefsym,iundefsym,nundefsym,tocoff,ntoc,modtaboff,nmodtab,extrefsymoff,nextrefsyms,indirectsymoff,nindirectsyms,extreloff,nextrel,locreloff,nlocrel;};
struct nlist_64 {u32 strx;u8 type,sect;unsigned short desc;u64 value;};

extern u32 mach_task_self_;
extern int mach_vm_allocate(u32,u64 *,u64,int);
extern int mach_vm_deallocate(u32,u64,u64);
extern int mach_vm_protect(u32,u64,u64,int,int);
extern void *mmap(void *,usize,int,int,int,long long);
extern int getpagesize(void);
extern isize write(int,const void *,usize);
extern int strcmp(const char *,const char *);
extern char *strstr(const char *,const char *);
extern u32 _dyld_image_count(void);
extern const struct mach_header_64 *_dyld_get_image_header(u32);
extern const char *_dyld_get_image_name(u32);
extern void _dyld_register_func_for_add_image(void (*)(const struct mach_header_64 *,isize));

#define LOW_START 0x130000000ULL
#define HEAP_LIMIT 0x200000000ULL
#define FALLBACK_END 0x1d0000000ULL
#define ARENA_SIZE 0x4000000ULL
#define MAP_FIXED 0x10
#define MAP_ANON 0x1000
#define MAP_FAILED ((void *)-1)

static void log_literal(const char *s, usize n) { write(2,s,n); }
#define LOG(s) log_literal(s,sizeof(s)-1)

/* Non-overwriting Mach VM reservation gives us ownership of the range. */
static void *reserve_and_map(u64 address,usize length,int prot,int flags,int fd,long long offset) {
    if (!length || address < 0x100000000ULL || address >= HEAP_LIMIT || length > HEAP_LIMIT-address) return MAP_FAILED;
    u64 reserved=address;
    if (mach_vm_allocate(mach_task_self_,&reserved,length,0) != 0) return MAP_FAILED;
    void *result=mmap((void *)reserved,length,prot,flags|MAP_FIXED,fd,offset);
    if (result==MAP_FAILED) mach_vm_deallocate(mach_task_self_,reserved,length);
    else LOG("HMAHeapFix: reserved Go heap below 8 GiB\n");
    return result;
}

void *hma_go_mmap(void *address,usize length,int prot,int flags,int fd,long long offset) {
    if (prot==0 && (flags&MAP_ANON) && !(flags&MAP_FIXED)) {
        u64 hint=(u64)address;
        if (hint && hint<HEAP_LIMIT) {
            void *mapped=reserve_and_map(hint,length,prot,flags,fd,offset);
            if (mapped!=MAP_FAILED) return mapped;
        } else if (!hint && length>=ARENA_SIZE && length<=FALLBACK_END-LOW_START) {
            for (u64 candidate=LOW_START;candidate<=FALLBACK_END-length;candidate+=ARENA_SIZE) {
                void *mapped=reserve_and_map(candidate,length,prot,flags,fd,offset);
                if (mapped!=MAP_FAILED) return mapped;
            }
        }
    }
    return mmap(address,length,prot,flags,fd,offset);
}

#ifndef HMA_HEAP_TEST
static void patch_slots(const struct mach_header_64 *header,isize slide) {
    if (header->magic!=0xfeedfacf) return;
    int target=0;
    for(u32 i=0;i<_dyld_image_count();i++) {
        if(_dyld_get_image_header(i)!=header) continue;
        const char *name=_dyld_get_image_name(i);
        target=name && strstr(name,"/MimicNetworking.framework/MimicNetworking")!=0;
        break;
    }
    if(!target)return;
    const struct symtab_command *symbols=0;
    const struct dysymtab_command *dynamic=0;
    const struct segment_64 *linkedit=0;
    const u8 *cursor=(const u8 *)(header+1);
    for(u32 i=0;i<header->ncmds;i++) {
        const struct load_command *command=(const struct load_command *)cursor;
        if(command->cmd==2)symbols=(const struct symtab_command *)cursor;
        if(command->cmd==11)dynamic=(const struct dysymtab_command *)cursor;
        if(command->cmd==25 && !strcmp(((const struct segment_64 *)cursor)->name,"__LINKEDIT"))linkedit=(const struct segment_64 *)cursor;
        cursor+=command->size;
    }
    if(!symbols || !dynamic || !linkedit)return;
    u64 base=slide+linkedit->vmaddr-linkedit->fileoff;
    const struct nlist_64 *names=(const struct nlist_64 *)(base+symbols->symoff);
    const char *strings=(const char *)(base+symbols->stroff);
    const u32 *indices=(const u32 *)(base+dynamic->indirectsymoff);
    cursor=(const u8 *)(header+1);
    for(u32 i=0;i<header->ncmds;i++) {
        const struct load_command *command=(const struct load_command *)cursor;
        if(command->cmd==25) {
            const struct segment_64 *segment=(const struct segment_64 *)cursor;
            const struct section_64 *sections=(const struct section_64 *)(segment+1);
            for(u32 j=0;j<segment->nsects;j++) {
                const struct section_64 *section=&sections[j];
                u32 type=section->flags&0xff;
                if(type!=6 && type!=7)continue;
                void **slots=(void **)(slide+section->addr);
                for(u64 k=0;k<section->size/sizeof(void *);k++) {
                    if(section->reserved1+k>=dynamic->nindirectsyms)continue;
                    u32 symbol=indices[section->reserved1+k];
                    if(symbol&0xc0000000 || symbol>=symbols->nsyms)continue;
                    u32 string=names[symbol].strx;
                    if(string>=symbols->strsize || strcmp(strings+string,"_mmap"))continue;
                    u64 page=(u64)&slots[k]&~((u64)getpagesize()-1);
                    if(mach_vm_protect(mach_task_self_,page,getpagesize(),0,0x13)!=0) {
                        LOG("HMAHeapFix: import slot protection failed\n");continue;
                    }
                    __atomic_store_n(&slots[k],(void *)hma_go_mmap,__ATOMIC_RELEASE);
                    if(!strcmp(segment->name,"__DATA_CONST"))mach_vm_protect(mach_task_self_,page,getpagesize(),0,1);
                    LOG("HMAHeapFix: installed scoped Go mmap fix\n");
                }
            }
        }
        cursor+=command->size;
    }
}

__attribute__((constructor)) static void initialize_heap_fix(void) {
    _dyld_register_func_for_add_image(patch_slots);
}
#endif
