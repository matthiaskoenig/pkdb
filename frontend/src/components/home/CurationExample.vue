<template>
  <div>
  <h2>Example study</h2>

    <p align="justify">
      The following example shows what information is extracted from a typical study
    </p>

    <p>
      <curation-example-image/>
    </p>

    <p>
      <single-study-button/>

  </p>
  </div>
</template>

<script>
import SingleStudyButton from "../lib/buttons/SingleStudyButton";

import {IconsMixin} from "@/icons";
import CurationExampleImage from "./CurationExampleImage";
export default {
  name: "CurationExample",
  mixins: [IconsMixin],
  components:{CurationExampleImage, SingleStudyButton}
}
</script>
