from QCanvasHelperBase import *
from QSettings import *
from QUtility import *

import numpy as np
import scipy.optimize as op
from matplotlib.widgets import Slider
from matplotlib.widgets import Button as mplButton

class QCanvasHelperManualPeakFit(QCanvasHelperBase):
    def display_current(self):
        self.clear_plot()

        fig = self.canv.figure
        fig.suptitle(self.get_spec_name(self.current))
        spectrum = self.read_spectrum(self.current)

        lower_bound = self.peak.get() - 30
        upper_bound = self.peak.get() + 30
        fit_area = QUtility.spectrum_slice(spectrum, lower_bound, upper_bound)
        self.wav_new = np.arange(fit_area[0][0], fit_area[-1][0], 0.01)
        self.fit_area_inter = QUtility.inter(fit_area, self.wav_new)

        pos_guess = fit_area[:,0][np.argmax(fit_area[:,1])]
        height_guess = fit_area[:,1][np.argmax(fit_area[:,1])]
        width_guess_l = 2
        width_guess_r = 2
        sigma_guess = 1
        const_guess = fit_area[-1,1]

        x0=[(pos_guess, height_guess*1.2, width_guess_l, width_guess_r, sigma_guess, const_guess)]
        bounds = [(pos_guess-3,pos_guess+3),(0.0,None),(0.0, None),(0.0,None), (0,1), (None,None)]
        fit_args = (self.wav_new, self.fit_area_inter)

        fit_res = op.minimize(QUtility.pseudovoigt_const, x0=x0, args=fit_args, method='SLSQP', bounds=bounds)
        fit = QUtility.pseudovoigt_fit(self.wav_new, *fit_res.x[:-1]) + fit_res.x[-1]

        sp = fig.add_subplot(111)
        sp.invert_xaxis()
        fig.subplots_adjust(left=0.2, bottom=0.4, right=0.85)

        sp.plot(fit_area[:,0], fit_area[:,1], 'k.', label='data')
        self.l, = sp.plot(self.wav_new, fit, 'g-')
        self.l2, = sp.plot(self.wav_new, (fit - self.fit_area_inter),'r-')
        sp.axhline(y=0, ls='--', color='k')
            
        sxpos = 0.2
        sypos = 0.3
        sydelta = -0.04
        swidth = 0.65
        sheight = 0.03

        #create slider(s)
        self.s_const, self.s_const_text, self.s_const10 = self.create_sym_slider(fig, 
            caption="const.",
            ypos=sypos, width=swidth, height=sheight,
            widthperc=1.2, initialvalue=fit_res.x[-1],
            hastenth=True,
            onchange=self.widget_update)

        sypos += sydelta
        self.s_x0, self.s_x0_text = self.create_slider(fig, 
            caption="peak pos.",
            ypos=sypos, width=swidth, height=sheight,
            minvalue=pos_guess-5, maxvalue=pos_guess+5, initialvalue=fit_res.x[0],
            valfmt="{:1.1f}",
            onchange=self.widget_update)

        sypos += sydelta
        self.s_I, self.s_I_text, self.s_I10 = self.create_slider(fig,
            caption='peak height',
            ypos=sypos, width=swidth, height=sheight,
            minvalue=0, maxvalue=fit_res.x[1]*1.3, initialvalue=fit_res.x[1],
            hastenth=True,
            onchange=self.widget_update)

        sypos += sydelta
        self.s_HWHM_l, self.s_HWHM_l_text = self.create_slider(fig,
            caption='l. half width',
            ypos=sypos, width=swidth, height=sheight,
            minvalue=0, maxvalue=fit_res.x[2]*3, initialvalue=fit_res.x[2],
            onchange=self.widget_update)

        sypos += sydelta
        self.s_HWHM_r, self.s_HWHM_r_text = self.create_slider(fig,
            caption='r. half width',
            ypos=sypos, width=swidth, height=sheight,
            minvalue=0, maxvalue=fit_res.x[3]*3, initialvalue=fit_res.x[3],
            onchange=self.widget_update)

        sypos += sydelta
        self.s_sigma, self.s_sigma_text = self.create_slider(fig,
            caption='Lorentz. contr.',
            ypos=sypos, width=swidth, height=sheight,
            minvalue=0, maxvalue=1, initialvalue=fit_res.x[4],
            onchange=self.widget_update, valfmt='{:.2f}')

        self.fig_text = self.create_fig_text(fig, 0.29, 0.8, 
            "Peak area:\n{} cm-2".format(np.round(QUtility.peak_area(self.s_I.val,
            self.s_HWHM_l.val, self.s_HWHM_r.val,
            self.s_sigma.val), 2)))

        # create reset button
        sypos += 2 * sydelta
        self.resetax = fig.add_axes([sxpos+swidth, sypos, 0.1, 0.04])
        self.reset_button = mplButton(self.resetax, 'Reset', color='lightgoldenrodyellow', hovercolor='0.975')

        sliders = (self.s_x0, self.s_I, self.s_HWHM_l, self.s_HWHM_r, self.s_sigma, self.s_const)
        self.reset_button.on_clicked( lambda event, arg=sliders: self.widget_reset(event, arg))

    
    def read_spectrum(self, idx):
        """read current spectrum
        """
        filename = self.specfiles[idx]
        if filename.lower().endswith('.csv'):
            spec = QUtility.read_spec(filename)
            return spec
        else:
            raise Exception("Unknown identifier " + filename + " in read_spectrum")

    def get_spec_name(self, idx):
        filename = self.specfiles[idx]
        if filename.lower().endswith('.csv'):
            return filename.split("/")[-1].split(".")[0]
        else:
            raise Exception("Unknown identifier " + filename + " in get_spec_name")

    def add_data(self, specfiles, peak):
        self.specfiles = specfiles
        self.peak = peak
        self.maxidx = len(self.specfiles)
        self.__std = QSettings.std

    def widget_reset(self, event, sliders):
        for slider in sliders:
            slider.reset()

    def widget_update(self, val):
        #get current slider values
        pos = self.s_x0.val
        I = self.get_disp_value(self.s_I, self.s_I10)
        HWHM_l = self.s_HWHM_l.val
        HWHM_r = self.s_HWHM_r.val
        sigma = self.s_sigma.val
        const = self.get_disp_value(self.s_const, self.s_const10)

        self.s_const_text.set(text="{:.2e}".format(const))
        self.s_x0_text.set(text="{:.1f}".format(pos))
        self.s_I_text.set(text="{:.2e}".format(I))
        self.s_HWHM_l_text.set(text="{:.2e}".format(HWHM_l))
        self.s_HWHM_r_text.set(text="{:.2e}".format(HWHM_r))
        self.s_sigma_text.set(text="{:.2f}".format(HWHM_r))

        self.l.set_ydata(QUtility.pseudovoigt_fit(self.wav_new, pos, I, HWHM_l, HWHM_r, sigma )+const)
        self.l2.set_ydata(QUtility.pseudovoigt_fit(self.wav_new, pos, I, HWHM_l, HWHM_r, sigma )+const-self.fit_area_inter)
        self.fig_text.set(text="Peak area:\n{} cm-2".format(np.round(QUtility.peak_area(I,
                                        HWHM_l, HWHM_r, sigma), 2)))
        
        