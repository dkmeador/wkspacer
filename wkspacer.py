#!/usr/bin/python

import os, sys
import json
import Tkinter as tk
import ttk as ttk
import tkMessageBox
import pexpect
from string import Template
import subprocess

class wkspacer(tk.Frame):



    def __init__(self, master=None):
        self.wrksp_cfgs = {}
        self.draw_main_window(master)
        self.load_wrksp_cfgs()

        self.user = os.getenv('USER')
        self.chip = os.getenv('CHIP')
        self.workarea = os.getenv('WORKAREA')
        self.subdir = os.getenv('TREE')
        if self.user is None:
            self.user = 'anonymous'
        if self.chip is None:
            self.chip = 'zt'
        if self.workarea is None:
            self.workarea = "/volume/" + self.chip + "-verif01/users/" + self.user + '/' + self.chip + '/ws01'
        if self.subdir is None:
            self.subdir = 'trinity'

        # Command strings
        #
        # Change the icmp4 configuration to allow writes to unopened files
        self.p4_allwrite_cmd = "icmp4 client -o | perl -ne \'if(/^\s*Options:/) {s/noallwrite/allwrite/;};print $_;\' | icmp4 client -i"

        self.sandup_setup_cmd = Template('mkdir -p ${workarea}/trinity/; ' + self.chip + 'SandUp')

        self.command_prompt = '[#\$] '
        self.machines = ['asic-shell01','asic-shell02','asic-shell03','asic-shell04','asic-shell05','asic-shell06']


    def draw_main_window(self, master=None):
        tk.Frame.__init__(self, master)
        top = self.winfo_toplevel()
        top.rowconfigure(0,weight=1)
        top.columnconfigure(0,weight=1)
        #Tk.Frame.title("Wkspacer")
        self.grid()
        self.grid(sticky=tk.N + tk.S + tk.E + tk.W)
        self.columnconfigure(1, weight=1)

        self.quitButton = tk.Button(self, text='Quit', width=10, pady=0, command=self.quit)
        self.b_add = tk.Button(self, text="Add", width=10, pady=0, command=self.draw_add_popup)
        self.b_edit = tk.Button(self, text="Edit", width=10, command=self.draw_edit_popup)
        self.b_rm = tk.Button(self, text="Remove", width=10, command=self.rm_wrksp_cfg)
        self.b_info = tk.Button(self, text="Info", width=10, command=self.draw_info_popup)
        self.b_sync = tk.Button(self, text="Rsync", width=10, command=self.draw_sync_popup)
        self.b_launch = tk.Button(self, text="Launch", width=10, command=self.launch_term)

        self.quitButton.grid(column=0, row=0)
        self.b_add.grid(column=0, row=1)
        self.b_edit.grid(column=0, row=2)
        self.b_rm.grid(column=0, row=3)
        self.b_info.grid(column=0, row=4)
        self.b_sync.grid(column=0, row=5)
        self.b_launch.grid(column=0, row=6)

        self.label = tk.Label(text="")
        self.label.grid(column=0, row=7, columnspan=3, sticky=tk.E + tk.W)

        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        self.scrollbar.grid(column=2, row=0, rowspan=7, sticky=tk.N + tk.S)

        ## Info line below listbox
        self.Lbox = tk.Listbox(self, selectmode=tk.SINGLE, width=80, name="lbox")
        self.Lbox.grid(column=1, row=0, rowspan=7, sticky=tk.E + tk.W)
        self.Lbox.bind('<<ListboxSelect>>', self.onselect)

        # Connect scrollbar to listbox
        self.scrollbar.config(command=self.Lbox.yview)
        self.Lbox.config(yscrollcommand=self.scrollbar.set)


    def draw_add_popup(self):
        popup = tk.Toplevel(self)
        popup.wm_title("Add a New Configuration")

        popup.columnconfigure(1,weight=1)
        # label = Tk.Label(popup, text="msg") #, font=NORM_FONT)
        # label.pack(side="top", fill="x", pady=10)

        cfg_name = tk.StringVar(popup, "Add Config Name")
        cfg_label = tk.Label(popup, text="Config name")
        cfg_entry = tk.Entry(popup, bd=5, textvariable=cfg_name)
        cfg_label.grid(column=0, row=0)
        cfg_entry.grid(column=1, row=0, sticky=tk.E + tk.W)

        # List of tuples
        default_cfgs = [('project', "Test_proj"),
                        ('chip', self.chip ),
                        ('workarea', self.workarea),
                        ('subdir', self.subdir),
                        ('bgcolor', 'white'),
                        ('fgcolor', 'black'),
                        ('machine', 'asic-shell01'),
                  #      ('setup_cmds', self.sandup_setup_cmd.safe_substitute() ),
                        ('localwksp', "Path_to_local_workspace"),
                        ('do_p4_setup', True),
                        ('p4_allwrite', True),
                        ('needs_setup', True)
                        ]

        rnum = 1
        entry_values = {}
        label_widg = []
        entry_widg = []
        for cfg in default_cfgs:
            (key, val) = cfg
            entry_values[key] = tk.StringVar(popup, value=val)
            label_widg.append(tk.Label(popup, text=key))
            if type(val) is bool:
                entry_widg.append(tk.Checkbutton(popup, bd=2, variable=entry_values[key]))
            elif key in ('machine'):
                entry_widg.append(ttk.Combobox(popup, textvariable=entry_values[key], values=self.machines ))
            else:
                entry_widg.append(tk.Entry(popup, bd=2, textvariable=entry_values[key]))
            label_widg[-1].grid(column=0, row=rnum)
            entry_widg[-1].grid(column=1, row=rnum, sticky=tk.E + tk.W)
            rnum += 1

        B1 = tk.Button(popup, text="Okay",
                       command=lambda: self.add_wrksp_cfgs(cfg_name.get(),
                            self.convert_stringvars_to_dict_obj(entry_values)) & (popup.destroy() == None))

        B2 = tk.Button(popup, text="Cancel", command=popup.destroy)

        B1.grid(row=rnum)
        B2.grid(row=rnum, column=1)



    def draw_edit_popup(self):

        list_items = self.Lbox.curselection()

        if (len(list_items) > 0):
            idx = list_items[0]
            popup = tk.Toplevel(self)
            popup.wm_title("Edit a Configuration")
            popup.columnconfigure(1, weight=1)

            cfg_nm = self.Lbox.get(idx)
            #to_edit = (Map (self.wrksp_cfgs[cfg_nm]))
            self.json_was_modified = 1

            cfg_name = tk.StringVar(popup, cfg_nm)
            cfg_label = tk.Label(popup, text="Config name")
            cfg_entry = tk.Entry(popup, bd=5, textvariable=cfg_name)
            cfg_label.grid(column=0, row=0)
            cfg_entry.grid(column=1, row=0, sticky=tk.E + tk.W)

            rnum = 1
            entry_values = {}
            for key, wksp in sorted(self.wrksp_cfgs[cfg_nm].iteritems()):
                entry_values[key] = tk.StringVar(popup, value=wksp)
                L1 = tk.Label(popup, text=key)
                L1.grid(column=0, row=rnum)
                if str(wksp) in ['0','1']:
                    E1 = (tk.Checkbutton(popup, bd=2, variable=entry_values[key]))
                    E1.grid(column=1, row=rnum, sticky=tk.E + tk.W)
                else:
                    E1 = (tk.Entry(popup, bd=2, textvariable=entry_values[key]))
                    E1.grid(column=1, row=rnum, sticky=tk.E + tk.W)
                rnum += 1


            B1 = tk.Button(popup, text="Okay",
                           command=lambda: self.add_wrksp_cfgs(cfg_name.get(),
                            self.convert_stringvars_to_dict_obj(entry_values)) & (popup.destroy() == None))

            B2 = tk.Button(popup, text="Cancel", command=popup.destroy)

            B1.grid(row=rnum)
            B2.grid(row=rnum, column=1)



    def draw_info_popup(self):

        list_items = self.Lbox.curselection()

        #for idx in list_items:
        if (len(list_items) > 0):
            idx = list_items[0]
            popup = tk.Toplevel(self)
            popup.wm_title("View a Configuration")
            cfg_nm = self.Lbox.get(idx)

            cfg_label = tk.Label(popup, bd=4, relief=tk.RIDGE, bg='khaki', text="Config name")
            cfg_entry = tk.Label(popup, bd=4, relief=tk.RIDGE, bg='khaki', text=cfg_nm)
            cfg_label.grid(column=0, row=0, sticky=tk.W+tk.E)
            cfg_entry.grid(column=1, row=0, sticky=tk.W+tk.E)

            rnum = 1
            for key, wksp in sorted(self.wrksp_cfgs[cfg_nm].iteritems()):
                L1 = tk.Label(popup, relief=tk.RIDGE, text=key)
                L1.grid(column=0, sticky=tk.W+tk.E, row=rnum)
                E1 = tk.Label(popup, text=wksp)
                E1.grid(column=1, sticky=tk.W, row=rnum)
                rnum += 1

            B1 = tk.Button(popup, text="Okay", command=lambda: popup.destroy())
            B1.grid(row=rnum)

    def draw_sync_popup(self):

        list_items = self.Lbox.curselection()

        #for idx in list_items:
        if (len(list_items) > 0):
            idx = list_items[0]
            popup = tk.Toplevel(self)
            popup.wm_title("View a Configuration")
            cfg_nm = self.Lbox.get(idx)

            cfg_label = tk.Label(popup, text="Config name")
            cfg_entry = tk.Label(popup, text=cfg_nm)
            cfg_label.grid(column=0, row=0)
            cfg_entry.grid(column=1, row=0)

            cfg_src_hdr = tk.Label(popup, text="Source")
            cfg_dest_hdr = tk.Label(popup, text="Destination")
            cfg_src_hdr.grid(column=0, row=1)
            cfg_dest_hdr.grid(column=2, row=1)

            if 'localwksp' not in self.wrksp_cfgs[cfg_nm]:
                self.wrksp_cfgs[cfg_nm]['localwksp'] = 'source_path'
            src_var = tk.StringVar(popup, value=self.wrksp_cfgs[cfg_nm]['localwksp'])

            cfg_src = tk.Entry(popup, textvariable=src_var)
            cfg_arrow = tk.Label(popup, text='-->')
            cfg_dest = tk.Label(popup, text=self.wrksp_cfgs[cfg_nm]['workarea'] + self.wrksp_cfgs[cfg_nm]['subdir'])
            cfg_src.grid(column=0, row=2)
            cfg_arrow.grid(column=1, row=2)
            cfg_dest.grid(column=2, row=2)

            B2 = tk.Button(popup, text="Sync", command=lambda: (self.rsync(self.wrksp_cfgs[cfg_nm]['localwksp'],
                                                                           self.wrksp_cfgs[cfg_nm]['workarea'] + self.wrksp_cfgs[cfg_nm]['subdir'],
                                                                           self.wrksp_cfgs[cfg_nm]['machine']) and
                                                                (popup.destroy() == None)))
            B2.grid(column=0, row=3)

            B2 = tk.Button(popup, text="Cancel", command=lambda: popup.destroy())
            B2.grid(column=2,row=3)

    def rsync(self,src,dest,machine):
        'Run rsync to push local changes to workspace'
        # make sure the source directory exists
        if (os.path.isdir(src)):
            subprocess.call(['rsync','-rtzv', src+'/', machine + ':/'+ dest ])
            return 1
        else:
            tkMessageBox.showerror("Bas source path","Source directory not found. Enter valid path")
            return 0


    def launch_term(self):
        list_items = self.Lbox.curselection()

        # for idx in list_items:
        if (len(list_items) > 0):
            idx = list_items[0]  # should only be one item in list. take the first only
            cfg_nm = self.Lbox.get(idx)
            cfg = self.wrksp_cfgs[cfg_nm]

            bgcolor = 'white'
            fgcolor = 'black'
            if ('bgcolor' in cfg):
                bgcolor = cfg['bgcolor']
            if ('fgcolor' in cfg):
                fgcolor = cfg['fgcolor']

            term_cmd = ['/opt/X11/bin/xterm']
            if bgcolor is not None:
                term_cmd += ['-bg', bgcolor]
            if fgcolor is not None:
                term_cmd += ['-fg', fgcolor]
            #term_cmd += ['-e', 'ssh', cfg['machine'], '-t', 'tmux attach -d -t \"' + cfg_nm + '\"']
            term_cmd += ['-e', 'ssh', cfg['machine'], '-t', 'tmux new -s \"' + cfg_nm + '\" || tmux attach -d -t \"' + cfg_nm + '\"']
            pid = subprocess.Popen(term_cmd).pid



    def convert_stringvars_to_dict_obj(self,svar_dict):
        myobj = Map()
        for key, svar in (svar_dict.iteritems()):
            myobj.__dict__[key] = svar.get()
        return myobj


    def onselect(self, evt):
        # Note here that Tk passes an event object to onselect()
        w = evt.widget
        index = int(w.curselection()[0])
        value = w.get(index)
        cfg = self.wrksp_cfgs[value]
        cfg_str = 'Proj: %-20s Chip: %-8s Path: %-50s' % (cfg["project"], cfg["chip"], cfg["workarea"] + cfg["subdir"])
        self.label.configure(text=cfg_str)

    def load_wrksp_cfgs(self):
        'Read the dot config file and populate the wrksp_cfgs array'
        self.load_workspaces()

    def add_wrksp_cfgs(self, cfg_name="test", cfg_obj=None, init=False):
        if (cfg_obj == None):
            cfg_obj = (Map(project="Test_proj",
                       chip="ZT",
                       workarea="/volume/zt/dmeador",
                       subdir="zt_fabio"))

        self.wrksp_cfgs[cfg_name] = cfg_obj.__dict__
        cfg = cfg_obj.__dict__

        # Make sure that workarea ends with a '/'
        if (cfg['workarea'][-1] != '/'):
            cfg['workarea'] = cfg['workarea'] + '/'

        if (init or cfg['needs_setup']):
            try:
                child = pexpect.spawn('ssh ' + self.user + '@' + cfg['machine'])
            except (OSError) as e:
                print >> sys.stderr, "Execution failed on launch of ssh session:", e
                return
            except:
                print "Unexpected error while spawning ssh"
                return

            child.expect('Last login')
            child.expect(self.command_prompt)
            # Use tmux for a presistent session by default
            if ('persistent' not in cfg or int(cfg['persistent'])==1):
                child.sendline("tmux new -s '" + cfg_name + "' || tmux attach -d -t '" + cfg_name + "'")
                child.expect(self.command_prompt)
                cfg['persistent'] = 1

            child.sendline('setenv WORKAREA ' + cfg['workarea'] )
            child.expect(self.command_prompt)
            child.sendline('mkdir -p $WORKAREA/trinity')
            child.expect(self.command_prompt)
            child.sendline('cd  $WORKAREA/trinity')
            child.expect(self.command_prompt)
            child.sendline('module add ' + cfg['chip'] + 'chip' )
            child.expect(self.command_prompt)

            if ('do_p4_setup' in cfg and int(cfg['do_p4_setup']) == 1):
                # icmp4 workspace setup
                child.timeout = 300 # wait for 5 minutes to SandUp
                child.sendline( cfg['chip'] + 'VerifUp')
                child.expect(self.command_prompt)
                cfg['do_p4_setup'] = False;

            if ('p4_allwrite' in cfg and int(cfg['p4_allwrite']) == 1):
                child.sendline(self.p4_allwrite_cmd)
                child.expect(self.command_prompt)

            # exit connected tmux session
            child.sendline('\002d') # Send C-b d to deattach tmux
            #  if (self.args.quit != True):
            #  child.interact()  # Give control of the child to the user.

        self.json_was_modified = 1
        self.update_listbox()
        return 1

    def rm_wrksp_cfg(self):
        # To query the selection, use curselection method. It returns a list of item indexes,
        items = self.Lbox.curselection()

        for idx in items:
            lbox_item = self.Lbox.get(idx)
            ok2rm = tkMessageBox.askokcancel('Confirm delete','Are you sure you want to delete the config named '+ lbox_item )
            if (ok2rm):
                # Clean up ICMP4 workarea??? This would not be simple. What if files are in the edit state?
                #TODO
                # Terminate tmux session if present
                #TODO
                del self.wrksp_cfgs[lbox_item]
                self.json_was_modified = 1
                self.Lbox.delete(idx)



    def load_workspaces(self):
        self.json_was_modified = 0
        with open(os.path.expanduser("~") + "/.wkspacer", 'r') as json_fileh:
            self.wrksp_cfgs = json.load(json_fileh)
        self.update_listbox()

    def update_listbox(self):
        entry_cnt = 0
        self.Lbox.delete(0, tk.END)
        #self.Lbox.config(selectbackground='white', selectforeground='black')
        self.Lbox.config(selectborderwidth=2)
        for key, wksp in sorted(self.wrksp_cfgs.iteritems()):
            self.Lbox.insert(entry_cnt, key)
            bgcolor = 'white'
            fgcolor = 'black'
            if ('bgcolor' in wksp):
                bgcolor = wksp['bgcolor']
            if ('fgcolor' in wksp):
                fgcolor = wksp['fgcolor']
            # this changes the background/foreground color of the item
            self.Lbox.itemconfig(entry_cnt, {'bg': bgcolor, 'fg': fgcolor})
            entry_cnt += 1

    def save_workspaces(self):
        if (self.json_was_modified):
            with open(os.path.expanduser("~") + "/.wkspacer", 'w') as json_fileh:
                json.dump(self.wrksp_cfgs, json_fileh, indent=3)

                # from collections import namedtuple


# MyStruct = namedtuple("workspace_cfg", "project chip workarea subdir")
# m = MyStruct("Test_proj", "ZT",  "/volume/zt/dmeador", "zt_fabio")
# print "WD" + m.project + m.chip  m.subdir
class Map:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)



if (__name__ == "__main__"):
    gui = wkspacer()
    gui.master.title('Wkspacer')
    gui.mainloop()
    gui.save_workspaces()



