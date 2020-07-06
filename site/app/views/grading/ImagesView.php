<?php

namespace app\views\grading;

use app\models\User;
use app\views\AbstractView;
use app\libraries\FileUtils;
use app\libraries\Utils;

class ImagesView extends AbstractView {
    /**
     * @param User[] $students
     * @return string
     */
    public function listStudentImages($students, $grader_sections, $has_full_access, $view) {
        $this->core->getOutput()->addBreadcrumb("Student Photos");
        $this->core->getOutput()->addInternalJs("drag-and-drop.js");
        $this->core->getOutput()->addInternalCss(FileUtils::joinPaths('fileinput.css'));
        $this->core->getOutput()->enableMobileViewport();

        //Assemble students into sections if they are in grader_sections based on the registration section.
        $sections = [];
        foreach ($students as $student) {
            $student_section = ($student->getRegistrationSection() === null) ? "NULL" : $student->getRegistrationSection();
            $student_belongs_to_grader = in_array($student_section, $grader_sections);

            // Full access no sections or view all
            if ($has_full_access && (empty($grader_sections) || $view === 'all')) {
                $sections[$student_section][] = $student;
            }
            // Full access view sections
            elseif ($has_full_access && $view === 'sections' && $student_belongs_to_grader) {
                $sections[$student_section][] = $student;
            }
            // Limited access only show their sections
            elseif ($student_belongs_to_grader) {
                $sections[$student_section][] = $student;
            }
        }

        $max_size = Utils::returnBytes(ini_get('upload_max_filesize'));
        $max_size_string = Utils::formatBytes("MB", $max_size) . " (" . Utils::formatBytes("KB", $max_size) . ")";

        $this->core->getOutput()->disableBuffer();
        return $this->core->getOutput()->renderTwigTemplate("grading/Images.twig", [
            "sections" => $sections,
            "has_full_access" => $has_full_access,
            "csrf_token" => $this->core->getCsrfToken(),
            "max_size_string" => $max_size_string,
            "view" => $view,
            "core" => $this->core,
            "has_sections" => !empty($grader_sections)
        ]);
    }
}
