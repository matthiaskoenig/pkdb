# Unreleased

- Security: the `pkdb` package and the backend require Pillow 13.0.0 or newer and lock it; Pillow 13.0.0 fixes 41 advisories of the earlier releases, among them the critical GHSA-v9pv-5gc8-w2m6, GHSA-5x8w-8jj5-q52h, GHSA-332p-7hrc-92wf, GHSA-w889-685w-c8fh and GHSA-8g5g-8vmr-9782. The former upper bound `<13` blocked projects which depend on `pkdb` from taking the fix.
